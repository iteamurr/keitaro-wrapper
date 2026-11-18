from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from keitaro_wrapper.application.ports.remote import RemoteOffer
from keitaro_wrapper.application.ports.repositories.catalog import IOfferCatalog
from keitaro_wrapper.common.clock import Clock
from keitaro_wrapper.infrastructure.persistence.models.integration import IntegrationRow
from keitaro_wrapper.infrastructure.persistence.models.offers import OfferRow


class ORMOfferCatalog(IOfferCatalog):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(self, offers: list[RemoteOffer]) -> None:
        binding = await self.session.scalar(
            select(IntegrationRow).where(IntegrationRow.id == 1).with_for_update()
        )
        await self.session.execute(delete(OfferRow))
        for offer in offers:
            self.session.add(OfferRow(id=offer.id, name=offer.name, state=offer.state))
        if binding:
            binding.catalog_updated_at = Clock.now()
        await self.session.flush()

    async def get(self) -> tuple[list[RemoteOffer], float]:
        binding = await self.session.get(IntegrationRow, 1)
        age = (
            (Clock.now() - binding.catalog_updated_at).total_seconds()
            if binding and binding.catalog_updated_at
            else float("inf")
        )
        rows = (await self.session.scalars(select(OfferRow))).all()
        return [
            RemoteOffer(row.id, row.name, row.state == "active", row.state) for row in rows
        ], age
