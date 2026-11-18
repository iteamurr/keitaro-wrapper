from keitaro_wrapper.application.ports.errors import GatewayError
from keitaro_wrapper.application.ports.remote import (
    CreationPlan,
    CreationSettings,
    PreparedWrite,
    RecoveryMatch,
    RemoteCampaign,
    RemoteOffer,
    RemoteStream,
    WriteResult,
)
from keitaro_wrapper.common.types import Document
from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.domain.streams.editor import OfferAllocation
from keitaro_wrapper.infrastructure.common.snapshots import freeze, thaw
from keitaro_wrapper.infrastructure.keitaro.client import KeitaroClient
from keitaro_wrapper.infrastructure.keitaro.creation import CreationCodec


class KeitaroGateway:
    """Anti-corruption layer: upstream JSON never escapes through the port."""

    def __init__(self, client: KeitaroClient) -> None:
        self.client = client

    async def write(self, request: PreparedWrite) -> WriteResult:
        data = await self.client.write(request.action, thaw(request.body), request.remote_id)
        return WriteResult(int(data["id"]), freeze(data))

    async def campaign(self, remote_id: int) -> RemoteCampaign:
        data = await self.client.campaign(remote_id)
        return RemoteCampaign(
            id=int(data["id"]),
            name=str(data["name"]),
            alias=str(data.get("alias", "")),
            state=str(data.get("state", "active")),
            snapshot=freeze(data),
        )

    async def streams(self, campaign_id: int) -> list[RemoteStream]:
        return [self._stream(data) for data in await self.client.streams(campaign_id)]

    async def stream(self, stream_id: int) -> RemoteStream:
        return self._stream(await self.client.stream(stream_id))

    def _stream(self, data: Document) -> RemoteStream:
        allocations, reason = self.client.inspect(data, {})
        return RemoteStream(
            id=int(data["id"]),
            name=str(data["name"]),
            position=int(data.get("position", 0)),
            snapshot=freeze(data),
            allocations=tuple(allocations),
            read_only_reason=reason,
        )

    async def offers(self) -> list[RemoteOffer]:
        return [self._offer(data) for data in await self.client.offers()]

    async def offer(self, offer_id: int) -> RemoteOffer:
        return self._offer(await self.client.offer(offer_id))

    @staticmethod
    def _offer(data: Document) -> RemoteOffer:
        state = str(data["state"])
        return RemoteOffer(int(data["id"]), str(data["name"]), state == "active", state)

    async def creation_settings(self) -> CreationSettings:
        data = await self.client.creation_settings()
        return CreationSettings(str(data["prefix"]), str(data["domain_url"]), freeze(data))

    def creation_domain(self, settings: Snapshot) -> str:
        return str(thaw(settings)["domain_url"])

    def prepare_creation(self, plan: CreationPlan, stage: str) -> PreparedWrite:
        if stage == "campaign":
            body = {
                **thaw(plan.settings)["campaign"],
                "name": plan.name,
                "alias": plan.alias,
                "state": "disabled",
                "type": "position",
                "notes": f"wrapper:{plan.operation_id}:campaign",
            }
            return PreparedWrite("create_campaign", freeze(body))
        if stage in ("geo", "fallback"):
            return PreparedWrite("create_stream", freeze(CreationCodec.stream_body(plan, stage)))
        if stage == "activate" and plan.campaign_id is not None:
            return PreparedWrite("update_campaign", freeze({"state": "active"}), plan.campaign_id)
        raise GatewayError("invalid_command", "Неизвестный этап создания кампании.")

    def verify_creation(
        self,
        plan: CreationPlan,
        campaign: RemoteCampaign,
        streams: list[RemoteStream],
        *,
        partial: bool = False,
    ) -> None:
        CreationCodec.verify(
            plan,
            thaw(campaign.snapshot),
            [thaw(s.snapshot) for s in streams],
            partial,
        )

    def prepare_publish(
        self,
        stream_id: int,
        allocations: tuple[OfferAllocation, ...],
    ) -> PreparedWrite:
        body = {
            "offers": [
                {"offer_id": offer.offer_id, "share": offer.weight, "state": "active"}
                for offer in allocations
            ]
        }
        return PreparedWrite("update_stream", freeze(body), stream_id)

    def matches(self, actual: Snapshot, expected: Snapshot) -> bool:
        return self.client.signature(thaw(actual)) == self.client.signature(thaw(expected))

    def matches_publish(
        self,
        actual: Snapshot,
        baseline: Snapshot,
        request: PreparedWrite,
    ) -> bool:
        desired = thaw(baseline)
        desired["offers"] = thaw(request.body)["offers"]
        return self.matches(actual, freeze(desired))

    async def recover(self, request: PreparedWrite, campaign_id: int | None) -> RecoveryMatch:
        body = thaw(request.body)
        if request.action == "create_campaign":
            candidates = [
                data
                for data in await self.client.campaigns()
                if data.get("alias") == body.get("alias") or data.get("notes") == body.get("notes")
            ]
            matches = [
                data
                for data in candidates
                if data.get("alias") == body.get("alias") and data.get("notes") == body.get("notes")
            ]
        elif request.action == "create_stream" and campaign_id is not None:
            candidates = [
                data
                for data in await self.client.streams(campaign_id)
                if data.get("comments") == body.get("comments")
            ]
            matches = candidates
        elif request.action == "update_campaign" and campaign_id is not None:
            data = await self.client.campaign(campaign_id)
            candidates = [data] if CreationCodec.contains(data, body) else []
            matches = candidates
        else:
            raise GatewayError(
                "invalid_checkpoint",
                "Неизвестная или неполная команда восстановления.",
            )
        verified = len(matches) == 1 and CreationCodec.contains(matches[0], body)
        return RecoveryMatch(int(matches[0]["id"]) if verified else None, bool(candidates))
