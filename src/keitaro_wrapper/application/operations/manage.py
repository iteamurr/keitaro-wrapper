from dataclasses import asdict, dataclass
from uuid import UUID

from keitaro_wrapper.application.campaigns.create import CreateCampaignUseCase
from keitaro_wrapper.application.campaigns.fetch import FetchCampaignUseCase
from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.application.common.synchronization import Synchronization
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.remote import PreparedWrite
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.application.streams.push import PushStreamUseCase
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class ManageOperationCommand:
    key: UUID
    operation_id: UUID
    expected_operation_revision: int
    action: str
    decision: str | None = None
    confirmation: bool = False
    note: str = ""


@dataclass
class ManageOperationUseCase:
    """Recover a durable operation without blindly replaying an uncertain write."""

    transactions: ITransactions
    sync: Synchronization
    fetch: FetchCampaignUseCase
    push: PushStreamUseCase
    create: CreateCampaignUseCase
    clock: IClock

    async def execute(self, command: ManageOperationCommand) -> Operation:
        payload = asdict(command)
        payload.pop("key")
        payload["operation_id"] = str(command.operation_id)
        async with self.transactions.transaction() as store:
            replay = await Commands.replay(store.operations, command.key, "control", payload)
            if replay:
                return await store.operations.require(command.operation_id)
            parent = await store.operations.require(command.operation_id)
            await store.campaigns.require(parent.campaign_id, lock=True)
            replay = await Commands.replay(store.operations, command.key, "control", payload)
            if replay:
                return await store.operations.require(command.operation_id)
            parent = await store.operations.require(command.operation_id)
            Commands.revision(parent.revision, command.expected_operation_revision)
            await Commands.unlocked(store.operations, parent.campaign_id, parent.id)
            parent.assert_control_allowed(command.action)
            if command.action == "resolve" and (
                not command.confirmation or not command.note.strip()
            ):
                raise DomainError(
                    "confirmation_required",
                    "Подтвердите завершение внешнего запроса и укажите результат проверки.",
                )
            if command.action == "resolve" and command.decision not in (
                "adopt_current",
                "not_applied",
            ):
                raise DomainError("invalid_command", "Неизвестное решение сверки.")
            if command.action == "resume" and parent.kind == "push":
                stream = await store.streams.require(parent.stream_id or 0)
                Commands.revision(stream.revision, int(parent.context["stream_revision"]))
            if command.action == "resume" and parent.kind in ("fetch", "import"):
                if any(s.dirty for s in await store.streams.list(parent.campaign_id)):
                    raise DomainError(
                        "dirty_campaign",
                        "Сначала отмените или опубликуйте черновики.",
                    )
            parent.begin_control(command.action, at=self.clock.now())
            receipt = Commands.build(
                command.key,
                "control",
                parent.campaign_id,
                payload,
                reserves=False,
                now=self.clock.now(),
            )
            receipt.checkpoint(
                parent_id=str(parent.id),
                at=self.clock.now(),
            )
            await store.operations.save(parent)
            await store.operations.save(receipt)
        try:
            if command.action == "resume":
                result = await self._resume(parent)
            elif command.action == "reconcile":
                result = await self.reconcile(parent)
            elif command.action == "resolve":
                result = await self.resolve(parent, command)
            else:
                raise DomainError("invalid_command", "Неизвестное действие операции.")
        except DomainError as error:
            result = await self.sync.fail(
                parent.id,
                GatewayError(error.code, error.message, uncertain=True),
            )
        async with self.transactions.transaction() as store:
            receipt = await store.operations.require(command.key)
            receipt.transition(
                "succeeded",
                {"operation_id": str(result.id), "campaign_id": str(result.campaign_id)},
                at=self.clock.now(),
            )
            await store.operations.save(receipt)
        return result

    async def _resume(self, operation: Operation) -> Operation:
        if operation.kind == "push":
            return await self.push.run(operation)
        if operation.kind == "create":
            return await self.create.run(operation)
        return await self.fetch.run(operation)

    async def reconcile(self, operation: Operation) -> Operation:
        if operation.kind in ("fetch", "import"):
            return await self.fetch.run(operation)
        if operation.kind == "push":
            return await self.push.confirm(operation)
        request = self.pending_write(operation)
        if request is None:
            return await self._finish(operation, "partial")
        match = await self.sync.gateway.recover(
            request,
            operation.context.get("campaign_remote_id"),
        )
        if match.id is None:
            return await self._finish(
                operation,
                "manual_review",
                "Результат не установлен. Повтор записи заблокирован.",
            )
        async with self.transactions.transaction() as store:
            await store.campaigns.require(operation.campaign_id, lock=True)
            current = await store.operations.require(operation.id)
            stage = str(current.context["stage"])
            if stage in ("campaign", "geo", "fallback"):
                current.checkpoint(
                    **{f"{stage}_remote_id": match.id},
                    at=self.clock.now(),
                )
            current.checkpoint(
                pending_action=None,
                at=self.clock.now(),
            )
            await store.operations.confirm_attempt(
                current.id,
                int(current.context["pending_attempt"]),
            )
            current.transition(
                "partial",
                at=self.clock.now(),
            )
            await store.operations.save(current)
            return current

    async def resolve(self, operation: Operation, command: ManageOperationCommand) -> Operation:
        if command.decision not in ("adopt_current", "not_applied"):
            raise DomainError("invalid_command", "Неизвестное решение сверки.")
        if operation.kind in ("fetch", "import"):
            return await self.fetch.run(operation)
        if operation.kind == "create":
            if command.decision == "adopt_current":
                return await self.reconcile(operation)
            # The operator confirms request completion; a positive match still prevents retry.
            request = self.pending_write(operation)
            if request is not None:
                match = await self.sync.gateway.recover(
                    request,
                    operation.context.get("campaign_remote_id"),
                )
                if match.possible_result:
                    raise DomainError(
                        "resolution_conflict",
                        "Найден возможный результат записи. Используйте сверку, а не повтор.",
                    )
            return await self._finish(
                operation,
                "partial" if operation.context.get("campaign_remote_id") else "failed",
                note=command.note,
                clear_pending=True,
            )
        assert operation.stream_id is not None
        remote = await self.sync.gateway.stream(operation.stream_id)
        if command.decision == "not_applied":
            if not self.sync.gateway.matches(remote.snapshot, operation.snapshot("base")):
                raise DomainError(
                    "resolution_conflict",
                    "Текущее состояние отличается от исходного. Отказ не подтверждён.",
                )
            return await self._finish(operation, "failed", note=command.note, clear_pending=True)
        async with self.transactions.transaction() as store:
            campaign = await store.campaigns.require(operation.campaign_id, lock=True)
            stream = await store.streams.require(operation.stream_id)
            stream.cancel()
            self.sync.accept_stream(
                stream,
                remote,
                {o.offer_id: o.name for o in stream.baseline.values()},
            )
            campaign.touch()
            await store.streams.save(stream)
            await store.campaigns.save(campaign)
            current = await store.operations.require(operation.id)
            current.checkpoint(
                manual_note=command.note,
                at=self.clock.now(),
            )
            current.transition(
                "succeeded",
                {"campaign_id": str(campaign.id), "adopted_external_state": True},
                at=self.clock.now(),
            )
            await store.operations.save(current)
            return current

    async def _finish(
        self,
        operation: Operation,
        status: str,
        message: str | None = None,
        note: str | None = None,
        clear_pending: bool = False,
    ) -> Operation:
        async with self.transactions.transaction() as store:
            await store.campaigns.require(operation.campaign_id, lock=True)
            current = await store.operations.require(operation.id)
            if clear_pending:
                current.checkpoint(
                    pending_action=None,
                    at=self.clock.now(),
                )
            if note:
                current.checkpoint(
                    manual_note=note,
                    at=self.clock.now(),
                )
            current.transition(
                status,
                code="manual_review" if message else None,
                message=message,
                at=self.clock.now(),
            )
            await store.operations.save(current)
            return current

    @staticmethod
    def pending_write(operation: Operation) -> PreparedWrite | None:
        action = operation.context.get("pending_action")
        if action is None:
            return None
        return PreparedWrite(
            action,
            operation.snapshot("pending_body"),
            operation.context.get("pending_remote_id"),
        )
