import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.common.synchronization import Synchronization
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class CommandExecutor:
    transactions: ITransactions
    sync: Synchronization
    timeout_seconds: float
    clock: IClock

    async def execute(self, key: UUID, work: Awaitable[Operation]) -> Operation:
        try:
            async with asyncio.timeout(self.timeout_seconds):
                return await work
        except DomainError as error:
            async with self.transactions.transaction() as store:
                operation = await store.operations.get(key)
            if operation is None:
                # No command was persisted by this rejected request. The client can
                # distinguish preflight errors from failures with an unknown outcome.
                raise DomainError(
                    error.code,
                    error.message,
                    {**error.details, "command_state": "not_started"},
                ) from None
            raise
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            result = await asyncio.shield(self.interrupted(key))
            if isinstance(error, asyncio.CancelledError):
                raise
            if result is not None:
                return result
            raise DomainError(
                "service_unavailable",
                "Операция не завершена. Проверьте соединение с БД и статус команды.",
            ) from None

    async def interrupted(self, key: UUID) -> Operation | None:
        async with self.transactions.transaction() as store:
            operation = await store.operations.get(key)
        if operation is None:
            return None
        if operation.kind == "control":
            parent_id = UUID(str(operation.context["parent_id"]))
            result = await self.sync.fail(
                parent_id,
                GatewayError(
                    "operation_interrupted",
                    "Выполнение прервано. Требуется сверка.",
                    uncertain=True,
                ),
            )
            async with self.transactions.transaction() as store:
                operation.transition(
                    "failed",
                    {"operation_id": str(parent_id)},
                    "operation_interrupted",
                    "Управляющая команда прервана.",
                    at=self.clock.now(),
                )
                await store.operations.save(operation)
            return result
        return await self.sync.fail(
            key,
            GatewayError(
                "operation_interrupted",
                "Выполнение прервано. Требуется сверка.",
                uncertain=operation.kind in ("push", "create"),
            ),
        )
