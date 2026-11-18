from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.application.common.synchronization import Synchronization
from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.remote import CreationPlan, RemoteCampaign, RemoteStream
from keitaro_wrapper.application.ports.storage import ITransactions
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation


@dataclass
class CreateCampaignCommand:
    key: UUID
    name: str
    country_code: str
    offer_id: int


@dataclass
class CreateCampaignUseCase:
    """Create an inactive campaign, verify its streams, then activate it."""

    transactions: ITransactions
    sync: Synchronization
    clock: IClock

    async def execute(self, command: CreateCampaignCommand) -> Operation:
        payload = {
            "name": command.name,
            "country_code": command.country_code,
            "offer_id": command.offer_id,
        }
        async with self.transactions.transaction() as store:
            previous = await Commands.replay(store.operations, command.key, "create", payload)
            if previous:
                return previous
        settings = await self.sync.gateway.creation_settings()
        await self.sync.gateway.offer(command.offer_id)
        name = (
            command.name
            if command.name.startswith(settings.prefix)
            else settings.prefix + command.name
        )
        async with self.transactions.transaction() as store:
            previous = await Commands.replay(store.operations, command.key, "create", payload)
            if previous:
                return previous
            campaign = Campaign(
                Identity.new(),
                name,
                alias=f"kw{command.key.hex[:20]}",
                state="creating",
            )
            await store.campaigns.save(campaign)
            operation = Commands.build(
                command.key,
                "create",
                campaign.id,
                payload,
                now=self.clock.now(),
            )
            operation.checkpoint(
                settings=settings.snapshot,
                alias=campaign.alias,
                name=name,
                at=self.clock.now(),
            )
            await store.operations.save(operation)
        return await self.run(operation)

    @staticmethod
    def plan(operation: Operation) -> CreationPlan:
        return CreationPlan(
            operation_id=operation.id,
            name=operation.context["name"],
            alias=operation.context["alias"],
            country_code=operation.payload["country_code"],
            offer_id=operation.payload["offer_id"],
            settings=operation.snapshot("settings"),
            campaign_id=operation.context.get("campaign_remote_id"),
            geo_id=operation.context.get("geo_remote_id"),
            fallback_id=operation.context.get("fallback_remote_id"),
        )

    async def run(self, operation: Operation) -> Operation:
        try:
            operation = await self.sync.operation(operation.id)
            plan = self.plan(operation)
            if plan.campaign_id is not None:
                remote = await self.sync.gateway.campaign(plan.campaign_id)
                streams = await self.sync.gateway.streams(plan.campaign_id)
                self.sync.gateway.verify_creation(plan, remote, streams, partial=True)
            else:
                await self.sync.write(
                    operation.id,
                    "campaign",
                    self.sync.gateway.prepare_creation(plan, "campaign"),
                )
            for stage in ("geo", "fallback"):
                operation = await self.sync.operation(operation.id)
                plan = self.plan(operation)
                if getattr(plan, f"{stage}_id") is None:
                    await self.sync.write(
                        operation.id,
                        stage,
                        self.sync.gateway.prepare_creation(plan, stage),
                    )
            operation = await self.sync.operation(operation.id)
            remote, streams, names = await self._verify_and_activate(operation)
            return await self._complete(operation, remote, streams, names)
        except DomainError as error:
            return await self.sync.fail(operation.id, error)

    async def _verify_and_activate(
        self,
        operation: Operation,
    ) -> tuple[RemoteCampaign, list[RemoteStream], dict[int, str]]:
        plan = self.plan(operation)
        assert plan.campaign_id is not None
        remote, streams, names = await self.sync.read_campaign(plan.campaign_id)
        self.sync.gateway.verify_creation(plan, remote, streams)
        if remote.state != "active":
            await self.sync.write(
                operation.id,
                "activate",
                self.sync.gateway.prepare_creation(plan, "activate"),
            )
            remote, streams, names = await self.sync.read_campaign(plan.campaign_id)
            self.sync.gateway.verify_creation(plan, remote, streams)
        if remote.state != "active":
            raise GatewayError(
                "verification_failed",
                "Не удалось подтвердить активацию кампании.",
                uncertain=True,
            )
        return remote, streams, names

    async def _complete(
        self,
        operation: Operation,
        remote: RemoteCampaign,
        streams: list[RemoteStream],
        names: dict[int, str],
    ) -> Operation:
        async with self.transactions.transaction() as store:
            campaign = await store.campaigns.require(operation.campaign_id, lock=True)
            current = await store.operations.require(operation.id)
            await self.sync.accept_campaign(store, campaign, remote, streams, names)
            campaign.set_tracking_url(
                self.sync.gateway.creation_domain(operation.snapshot("settings"))
            )
            await store.campaigns.save(campaign)
            current.transition(
                "succeeded",
                {
                    "campaign_id": str(campaign.id),
                    "keitaro_campaign_id": campaign.remote_id,
                    "url": campaign.url,
                },
                at=self.clock.now(),
            )
            await store.operations.save(current)
            return current
