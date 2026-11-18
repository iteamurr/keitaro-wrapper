from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.campaigns.fetch import FetchCampaignUseCase
from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class ImportCampaignCommand:
    key: UUID
    remote_id: int


@dataclass
class ImportCampaignUseCase:
    """Reserve the first import without replacing an existing editor."""

    transactions: ITransactions
    fetch: FetchCampaignUseCase
    clock: IClock

    async def execute(self, command: ImportCampaignCommand) -> Operation:
        payload = {"remote_id": command.remote_id}
        async with self.transactions.transaction() as store:
            previous = await Commands.replay(store.operations, command.key, "import", payload)
            if previous:
                return previous
            existing = await store.campaigns.by_remote(command.remote_id)
            if existing:
                operation = Commands.build(
                    command.key,
                    "import",
                    existing.id,
                    payload,
                    reserves=False,
                    now=self.clock.now(),
                )
                operation.transition(
                    "succeeded",
                    {"campaign_id": str(existing.id)},
                    at=self.clock.now(),
                )
                await store.operations.save(operation)
                return operation
            campaign = Campaign(Identity.new(), f"Кампания #{command.remote_id}", command.remote_id)
            await store.campaigns.save(campaign)
            operation = Commands.build(
                command.key,
                "import",
                campaign.id,
                payload,
                now=self.clock.now(),
            )
            await store.operations.save(operation)
        return await self.fetch.run(operation)
