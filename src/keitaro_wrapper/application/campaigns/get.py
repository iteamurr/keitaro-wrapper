from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from keitaro_wrapper.application.operations.views import OperationView
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.application.streams.views import StreamView


@dataclass(frozen=True)
class CampaignDetail:
    id: UUID
    keitaro_id: int | None
    name: str
    revision: int
    state: str
    url: str | None
    busy: bool
    can_fetch: bool
    last_fetched_at: datetime | None
    streams: list[StreamView]
    operations: list[OperationView]


@dataclass
class GetCampaignUseCase:
    transactions: ITransactions

    async def execute(self, campaign_id: UUID) -> CampaignDetail:
        async with self.transactions.transaction() as store:
            campaign = await store.campaigns.require(campaign_id)
            streams = await store.streams.list(campaign_id)
            busy = await store.operations.active(campaign_id) is not None
            operations = await store.operations.list(campaign_id)
        return CampaignDetail(
            id=campaign.id,
            keitaro_id=campaign.remote_id,
            name=campaign.name,
            revision=campaign.revision,
            state=campaign.state,
            url=campaign.url,
            busy=busy,
            can_fetch=not busy
            and not any(stream.dirty for stream in streams)
            and campaign.remote_id is not None,
            last_fetched_at=campaign.last_fetched_at,
            streams=[StreamView.from_entity(stream, busy=busy) for stream in streams],
            operations=[OperationView.from_entity(operation) for operation in operations],
        )
