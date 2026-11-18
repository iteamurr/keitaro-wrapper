from dataclasses import asdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from keitaro_wrapper.application.ports.repositories.campaigns import ICampaigns
from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.infrastructure.persistence.models.campaigns import CampaignRow


class ORMCampaigns(ICampaigns):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, entity: Campaign) -> None:
        await self.session.merge(CampaignRow(**asdict(entity)))
        await self.session.flush()

    async def get(self, key: UUID, lock: bool = False) -> Campaign | None:
        query = (
            select(CampaignRow)
            .where(CampaignRow.id == key)
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        row = await self.session.scalar(query)
        return self._campaign(row) if row else None

    async def by_remote(self, remote_id: int) -> Campaign | None:
        row = await self.session.scalar(
            select(CampaignRow).where(CampaignRow.remote_id == remote_id)
        )
        return self._campaign(row) if row else None

    async def list(self, limit: int = 100, offset: int = 0) -> list[Campaign]:
        rows = (
            await self.session.scalars(
                select(CampaignRow)
                .order_by(CampaignRow.name, CampaignRow.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [self._campaign(row) for row in rows]

    async def count(self) -> int:
        return int(await self.session.scalar(select(func.count()).select_from(CampaignRow)) or 0)

    @classmethod
    def _campaign(cls, row: CampaignRow) -> Campaign:
        return Campaign(**{key: getattr(row, key) for key in Campaign.__dataclass_fields__})
