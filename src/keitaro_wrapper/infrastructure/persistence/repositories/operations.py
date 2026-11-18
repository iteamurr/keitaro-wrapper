from dataclasses import asdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from keitaro_wrapper.application.ports.repositories.operations import IOperations
from keitaro_wrapper.common.clock import Clock
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.domain.operations.entity import RESERVED_STATUSES, Operation
from keitaro_wrapper.infrastructure.common.snapshots import freeze, thaw
from keitaro_wrapper.infrastructure.persistence.models.operations import AttemptRow, OperationRow


class ORMOperations(IOperations):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, entity: Operation) -> None:
        data = asdict(entity)
        data["context"] = {
            key: thaw(value) if isinstance(value, Snapshot) else value
            for key, value in entity.context.items()
        }
        await self.session.merge(OperationRow(**data))
        await self.session.flush()

    async def record_attempt(self, operation: Operation, stage: str, expected: Snapshot) -> int:
        number = (
            int(
                await self.session.scalar(
                    select(func.coalesce(func.max(AttemptRow.number), 0)).where(
                        AttemptRow.operation_id == operation.id
                    )
                )
                or 0
            )
            + 1
        )
        self.session.add(
            AttemptRow(
                id=Identity.new(),
                operation_id=operation.id,
                number=number,
                stage=stage,
                expected=thaw(expected),
                state="sending",
                created_at=Clock.now(),
            )
        )
        await self.session.flush()
        return number

    async def confirm_attempt(self, operation_id: UUID, number: int) -> None:
        row = await self.session.scalar(
            select(AttemptRow).where(
                AttemptRow.operation_id == operation_id,
                AttemptRow.number == number,
            )
        )
        if row:
            row.state = "confirmed"

    async def get(self, key: UUID) -> Operation | None:
        row = await self.session.get(OperationRow, key, populate_existing=True)
        return self._operation(row) if row else None

    async def active(self, campaign_id: UUID) -> Operation | None:
        row = await self.session.scalar(
            select(OperationRow).where(
                OperationRow.campaign_id == campaign_id,
                OperationRow.reserves_campaign.is_(True),
                OperationRow.status.in_(RESERVED_STATUSES),
            )
        )
        return self._operation(row) if row else None

    async def list(self, campaign_id: UUID) -> list[Operation]:
        rows = (
            await self.session.scalars(
                select(OperationRow)
                .where(
                    OperationRow.campaign_id == campaign_id,
                    OperationRow.reserves_campaign.is_(True),
                )
                .order_by(OperationRow.created_at.desc())
                .limit(20)
            )
        ).all()
        return [self._operation(row) for row in rows]

    @classmethod
    def _operation(cls, row: OperationRow) -> Operation:
        data = {key: getattr(row, key) for key in Operation.__dataclass_fields__}
        context = dict(row.context)
        # Pre-refactor Push checkpoints stored a bare upstream offers list.
        if "offers" in context and "publication" not in context:
            offers = context.pop("offers")
            context["publication"] = {"offers": offers}
            context["offer_ids"] = [offer["offer_id"] for offer in offers]
        for key in ("settings", "base", "publication", "pending_body", "last_response"):
            if key in context:
                context[key] = freeze(context[key])
        data["context"] = context
        return Operation(**data)
