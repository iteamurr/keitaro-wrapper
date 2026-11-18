from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.application.common.synchronization import Synchronization
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class FetchCampaignCommand:
    key: UUID
    campaign_id: UUID
    expected_revision: int


@dataclass
class FetchCampaignUseCase:
    """Reserve and atomically accept a complete external campaign snapshot."""

    transactions: ITransactions
    sync: Synchronization
    clock: IClock

    async def execute(self, command: FetchCampaignCommand) -> Operation:
        payload = {
            "campaign_id": str(command.campaign_id),
            "expected_revision": command.expected_revision,
        }
        async with self.transactions.transaction() as store:
            previous = await Commands.replay(store.operations, command.key, "fetch", payload)
            if previous:
                return previous
            campaign = await store.campaigns.require(command.campaign_id, lock=True)
            previous = await Commands.replay(store.operations, command.key, "fetch", payload)
            if previous:
                return previous
            await Commands.unlocked(store.operations, campaign.id)
            Commands.revision(campaign.revision, command.expected_revision)
            if campaign.remote_id is None:
                raise DomainError("not_found", "Кампания ещё не создана в Keitaro.")
            if any(stream.dirty for stream in await store.streams.list(campaign.id)):
                raise DomainError(
                    "dirty_campaign",
                    "Сначала опубликуйте или отмените изменения потоков.",
                )
            operation = Commands.build(
                command.key,
                "fetch",
                campaign.id,
                payload,
                now=self.clock.now(),
            )
            await store.operations.save(operation)
        return await self.run(operation)

    async def run(self, operation: Operation) -> Operation:
        try:
            async with self.transactions.transaction() as store:
                campaign = await store.campaigns.require(operation.campaign_id)
            if campaign.remote_id is None:
                raise DomainError("not_found", "Кампания ещё не создана в Keitaro.")
            remote, streams, names = await self.sync.read_campaign(campaign.remote_id)
            async with self.transactions.transaction() as store:
                campaign = await store.campaigns.require(operation.campaign_id, lock=True)
                current = await store.operations.require(operation.id)
                await Commands.unlocked(store.operations, campaign.id, current.id)
                await self.sync.accept_campaign(store, campaign, remote, streams, names)
                current.transition(
                    "succeeded",
                    {"campaign_id": str(campaign.id)},
                    at=self.clock.now(),
                )
                await store.operations.save(current)
                return current
        except DomainError as error:
            return await self.sync.fail(operation.id, error)
