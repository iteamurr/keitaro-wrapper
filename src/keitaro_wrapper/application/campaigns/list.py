from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.common.pagination import Page, Pagination


@dataclass(frozen=True)
class CampaignSummary:
    id: UUID
    keitaro_id: int | None
    name: str
    state: str
    revision: int


@dataclass
class ListCampaignsUseCase:
    transactions: ITransactions

    async def execute(self, pagination: Pagination) -> Page[CampaignSummary]:
        async with self.transactions.transaction() as store:
            campaigns = await store.campaigns.list(pagination.limit, pagination.offset)
            total = await store.campaigns.count()
        items = [CampaignSummary(c.id, c.remote_id, c.name, c.state, c.revision) for c in campaigns]
        return Page(items, total, pagination.limit, pagination.offset)
