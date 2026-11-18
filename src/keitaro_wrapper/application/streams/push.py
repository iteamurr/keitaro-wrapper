from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.application.common.synchronization import Synchronization
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.remote import PreparedWrite
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class PushStreamCommand:
    key: UUID
    stream_id: int
    expected_revision: int


@dataclass
class PushStreamUseCase:
    """Publish a fixed editor revision after checking for external conflicts."""

    transactions: ITransactions
    sync: Synchronization
    clock: IClock

    async def execute(self, command: PushStreamCommand) -> Operation:
        payload = {"stream_id": command.stream_id, "expected_revision": command.expected_revision}
        async with self.transactions.transaction() as store:
            previous = await Commands.replay(store.operations, command.key, "push", payload)
            if previous:
                return previous
            stream = await store.streams.require(command.stream_id)
            campaign = await store.campaigns.require(stream.campaign_id, lock=True)
            previous = await Commands.replay(store.operations, command.key, "push", payload)
            if previous:
                return previous
            await Commands.unlocked(store.operations, campaign.id)
            stream = await store.streams.require(command.stream_id)
            Commands.revision(stream.revision, command.expected_revision)
            target = stream.publication()
            request = self.sync.gateway.prepare_publish(stream.id, target)
            operation = Commands.build(
                command.key,
                "push",
                campaign.id,
                payload,
                stream.id,
                now=self.clock.now(),
            )
            operation.checkpoint(
                base=stream.remote_baseline,
                publication=request.body,
                offer_ids=[offer.offer_id for offer in target],
                stream_revision=stream.revision,
                at=self.clock.now(),
            )
            await store.operations.save(operation)
        return await self.run(operation)

    @staticmethod
    def publication(operation: Operation) -> PreparedWrite:
        assert operation.stream_id is not None
        return PreparedWrite(
            "update_stream",
            operation.snapshot("publication"),
            operation.stream_id,
        )

    async def run(self, operation: Operation) -> Operation:
        assert operation.stream_id is not None
        confirmed_write = False
        try:
            try:
                current = await self.sync.gateway.stream(operation.stream_id)
            except GatewayError as error:
                if error.code == "remote_not_found":
                    raise DomainError(
                        "remote_conflict",
                        "Поток недоступен в Keitaro. Выполните Cancel и Fetch.",
                    ) from None
                raise
            baseline = operation.snapshot("base")
            if not self.sync.gateway.matches(current.snapshot, baseline):
                raise DomainError(
                    "remote_conflict",
                    "Поток изменён в Keitaro. Выполните Cancel и Fetch.",
                )
            for offer_id in operation.context["offer_ids"]:
                await self.sync.gateway.offer(offer_id)
            request = self.publication(operation)
            if not self.sync.gateway.matches_publish(current.snapshot, baseline, request):
                await self.sync.write(operation.id, "publish", request)
                confirmed_write = True
            return await self.confirm(operation)
        except DomainError as error:
            if confirmed_write:
                error = GatewayError(error.code, error.message, uncertain=True)
            return await self.sync.fail(operation.id, error)

    async def confirm(self, operation: Operation) -> Operation:
        assert operation.stream_id is not None
        remote = await self.sync.gateway.stream(operation.stream_id)
        if not self.sync.gateway.matches_publish(
            remote.snapshot,
            operation.snapshot("base"),
            self.publication(operation),
        ):
            raise GatewayError(
                "verification_failed",
                "Результат публикации не совпал с ожидаемым. Нужна сверка.",
                uncertain=True,
            )
        async with self.transactions.transaction() as store:
            campaign = await store.campaigns.require(operation.campaign_id, lock=True)
            current = await store.operations.require(operation.id)
            stream = await store.streams.require(operation.stream_id)
            self.sync.accept_stream(
                stream,
                remote,
                {o.offer_id: o.name for o in stream.draft.values()},
            )
            campaign.touch()
            current.transition(
                "succeeded",
                {"campaign_id": str(campaign.id), "stream_id": stream.id},
                at=self.clock.now(),
            )
            await store.streams.save(stream)
            await store.campaigns.save(campaign)
            await store.operations.save(current)
            return current
