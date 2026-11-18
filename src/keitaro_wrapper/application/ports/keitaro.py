from typing import Protocol

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
from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.domain.streams.editor import OfferAllocation


class IKeitaroGateway(Protocol):
    async def write(self, request: PreparedWrite) -> WriteResult: ...
    async def campaign(self, remote_id: int) -> RemoteCampaign: ...
    async def streams(self, campaign_id: int) -> list[RemoteStream]: ...
    async def stream(self, stream_id: int) -> RemoteStream: ...
    async def offers(self) -> list[RemoteOffer]: ...
    async def offer(self, offer_id: int) -> RemoteOffer: ...
    async def creation_settings(self) -> CreationSettings: ...
    def creation_domain(self, settings: Snapshot) -> str: ...
    def prepare_creation(self, plan: CreationPlan, stage: str) -> PreparedWrite: ...
    def verify_creation(
        self,
        plan: CreationPlan,
        campaign: RemoteCampaign,
        streams: list[RemoteStream],
        *,
        partial: bool = False,
    ) -> None: ...
    def prepare_publish(
        self,
        stream_id: int,
        allocations: tuple[OfferAllocation, ...],
    ) -> PreparedWrite: ...
    def matches(self, actual: Snapshot, expected: Snapshot) -> bool: ...
    def matches_publish(
        self,
        actual: Snapshot,
        baseline: Snapshot,
        request: PreparedWrite,
    ) -> bool: ...
    async def recover(self, request: PreparedWrite, campaign_id: int | None) -> RecoveryMatch: ...
