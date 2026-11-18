from dataclasses import dataclass, replace
from uuid import UUID

from keitaro_wrapper.application.ports.clock import IClock
from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.keitaro import IKeitaroGateway
from keitaro_wrapper.application.ports.remote import (
    PreparedWrite,
    RemoteCampaign,
    RemoteStream,
    WriteResult,
)
from keitaro_wrapper.application.ports.storage import ITransactions, IUnitOfWork
from keitaro_wrapper.domain.campaigns.entity import Campaign
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.operations.entity import Operation
from keitaro_wrapper.domain.streams.editor import StreamEditor


@dataclass
class Synchronization:
    transactions: ITransactions
    gateway: IKeitaroGateway
    clock: IClock

    async def read_campaign(
        self,
        remote_id: int,
    ) -> tuple[RemoteCampaign, list[RemoteStream], dict[int, str]]:
        campaign = await self.gateway.campaign(remote_id)
        streams = await self.gateway.streams(remote_id)
        catalog = await self.gateway.offers()
        return campaign, streams, {o.id: o.name for o in catalog}

    async def accept_campaign(
        self,
        store: IUnitOfWork,
        campaign: Campaign,
        remote: RemoteCampaign,
        streams: list[RemoteStream],
        names: dict[int, str],
    ) -> None:
        known = {s.id: s for s in await store.streams.list(campaign.id)}
        incoming = set()
        for data in streams:
            key = data.id
            incoming.add(key)
            editor = known.get(key) or StreamEditor(
                key,
                campaign.id,
                data.name,
                data.position,
                data.snapshot,
            )
            self.accept_stream(editor, data, names)
            await store.streams.save(editor)
        for key, editor in known.items():
            if key not in incoming:
                editor.mark_missing()
                await store.streams.save(editor)
        campaign.accept(
            remote.id,
            remote.name,
            remote.alias,
            remote.state,
            self.clock.now(),
        )
        await store.campaigns.save(campaign)

    async def fail(self, operation_id: UUID, error: DomainError) -> Operation:
        async with self.transactions.transaction() as store:
            operation = await store.operations.require(operation_id)
            await store.campaigns.require(operation.campaign_id, lock=True)
            operation = await store.operations.require(operation_id)
            if operation.status != "running":
                return operation
            status = "failed"
            if isinstance(error, GatewayError) and error.uncertain:
                status = "unknown"
            elif error.code == "remote_conflict":
                status = "conflict"
            elif operation.kind == "create" and operation.context.get("campaign_remote_id"):
                status = "partial"
            operation.transition(
                status,
                code=error.code,
                message=error.message,
                at=self.clock.now(),
            )
            await store.operations.save(operation)
            return operation

    async def operation(self, operation_id: UUID) -> Operation:
        async with self.transactions.transaction() as store:
            return await store.operations.require(operation_id)

    async def write(
        self,
        operation_id: UUID,
        stage: str,
        request: PreparedWrite,
    ) -> WriteResult:
        async with self.transactions.transaction() as store:
            operation = await store.operations.require(operation_id)
            await store.campaigns.require(operation.campaign_id, lock=True)
            if operation.status != "running":
                raise DomainError("operation_busy", "Операция больше не исполняется.")
            attempt = await store.operations.record_attempt(operation, stage, request.body)
            operation.checkpoint(
                stage=stage,
                pending_action=request.action,
                pending_body=request.body,
                pending_remote_id=request.remote_id,
                pending_attempt=attempt,
                at=self.clock.now(),
            )
            await store.operations.save(operation)
        response = await self.gateway.write(request)
        async with self.transactions.transaction() as store:
            operation = await store.operations.require(operation_id)
            await store.campaigns.require(operation.campaign_id, lock=True)
            await store.operations.confirm_attempt(operation_id, attempt)
            operation.checkpoint(
                last_response=response.snapshot,
                pending_action=None,
                at=self.clock.now(),
            )
            if stage in ("campaign", "geo", "fallback"):
                operation.checkpoint(
                    **{f"{stage}_remote_id": response.id},
                    at=self.clock.now(),
                )
            await store.operations.save(operation)
        return response

    @staticmethod
    def accept_stream(editor: StreamEditor, remote: RemoteStream, names: dict[int, str]) -> None:
        allocations = [
            replace(offer, name=names.get(offer.offer_id, offer.name))
            for offer in remote.allocations
        ]
        editor.accept(
            remote.snapshot,
            allocations,
            remote.read_only_reason,
            name=remote.name,
            position=remote.position,
        )
