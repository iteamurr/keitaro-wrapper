from dataclasses import dataclass

from keitaro_wrapper.application.ports.keitaro import IKeitaroGateway
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.common.pagination import Page, Pagination


@dataclass(frozen=True)
class OfferSummary:
    id: int
    name: str


@dataclass(frozen=True)
class SearchOffersQuery:
    query: str
    pagination: Pagination


@dataclass
class SearchOffersUseCase:
    """Search a short-lived catalog without exposing private offer configuration."""

    transactions: ITransactions
    gateway: IKeitaroGateway

    async def execute(self, command: SearchOffersQuery) -> Page[OfferSummary]:
        query, pagination = command.query, command.pagination
        async with self.transactions.transaction() as store:
            catalog, age = await store.catalog.get()
        if age >= 60:
            catalog = await self.gateway.offers()
            async with self.transactions.transaction() as store:
                await store.catalog.replace(catalog)
        needle = query.strip().casefold()
        matches = [
            o for o in catalog if o.active and (needle in o.name.casefold() or needle == str(o.id))
        ]
        matches.sort(key=lambda o: (o.name.casefold(), o.id))
        items = [
            OfferSummary(offer.id, offer.name)
            for offer in matches[pagination.offset : pagination.offset + pagination.limit]
        ]
        return Page(items, len(matches), pagination.limit, pagination.offset)
