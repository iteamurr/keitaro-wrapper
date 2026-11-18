from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.domain.common.snapshot import Snapshot
from keitaro_wrapper.domain.streams.editor import OfferAllocation


@dataclass(frozen=True)
class RemoteOffer:
    id: int
    name: str
    active: bool
    state: str


@dataclass(frozen=True)
class RemoteCampaign:
    id: int
    name: str
    alias: str
    state: str
    snapshot: Snapshot


@dataclass(frozen=True)
class RemoteStream:
    id: int
    name: str
    position: int
    snapshot: Snapshot
    allocations: tuple[OfferAllocation, ...]
    read_only_reason: str | None


@dataclass(frozen=True)
class CreationSettings:
    prefix: str
    domain_url: str
    snapshot: Snapshot


@dataclass(frozen=True)
class CreationPlan:
    operation_id: UUID
    name: str
    alias: str
    country_code: str
    offer_id: int
    settings: Snapshot
    campaign_id: int | None = None
    geo_id: int | None = None
    fallback_id: int | None = None


@dataclass(frozen=True)
class PreparedWrite:
    action: str
    body: Snapshot
    remote_id: int | None = None


@dataclass(frozen=True)
class WriteResult:
    id: int
    snapshot: Snapshot


@dataclass(frozen=True)
class RecoveryMatch:
    """A unique, verified match; ambiguous candidates are never confirmed."""

    id: int | None
    possible_result: bool
