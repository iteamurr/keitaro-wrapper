from datetime import datetime
from uuid import UUID

from keitaro_wrapper.application.ports.repositories.operations import IOperations
from keitaro_wrapper.common.fingerprint import Fingerprint
from keitaro_wrapper.common.types import Document
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


class Commands:
    @classmethod
    async def replay(
        cls,
        operations: IOperations,
        key: UUID,
        kind: str,
        payload: Document,
    ) -> Operation | None:
        operation = await operations.get(key)
        if operation and operation.fingerprint != Fingerprint.of([kind, payload]):
            raise DomainError(
                "idempotency_conflict",
                "Этот ключ уже использован для другой команды.",
            )
        return operation

    @classmethod
    async def unlocked(
        cls,
        operations: IOperations,
        campaign_id: UUID,
        owner: UUID | None = None,
    ) -> None:
        active = await operations.active(campaign_id)
        if active and active.id != owner:
            raise DomainError(
                "campaign_busy",
                "Кампания занята незавершённой операцией.",
                {"operation_id": str(active.id)},
            )

    @classmethod
    def revision(cls, actual: int, expected: int) -> None:
        if actual != expected:
            raise DomainError(
                "stale_revision",
                "Данные изменились. Обновите страницу.",
                {"revision": actual},
            )

    @classmethod
    def build(
        cls,
        key: UUID,
        kind: str,
        campaign_id: UUID,
        payload: Document,
        stream_id: int | None = None,
        reserves: bool = True,
        *,
        now: datetime,
    ) -> Operation:
        return Operation(
            key,
            kind,
            campaign_id,
            Fingerprint.of([kind, payload]),
            payload,
            stream_id=stream_id,
            reserves_campaign=reserves,
            created_at=now,
            updated_at=now,
        )
