from __future__ import annotations

from dataclasses import dataclass

from keitaro_wrapper.domain.streams.editor import StreamEditor


@dataclass(frozen=True)
class OfferAllocationView:
    offer_id: int
    name: str
    weight: int
    active: bool
    pinned: bool
    external_state: str
    status: str


@dataclass(frozen=True)
class StreamView:
    id: int
    name: str
    revision: int
    dirty: bool
    available: bool
    read_only_reason: str | None
    total: int
    offers: list[OfferAllocationView]
    can_edit: bool
    can_cancel: bool
    can_push: bool

    @classmethod
    def from_entity(cls, stream: StreamEditor, *, busy: bool) -> StreamView:
        can_edit = not busy and stream.available and not stream.read_only_reason
        return cls(
            id=stream.id,
            name=stream.name,
            revision=stream.revision,
            dirty=stream.dirty,
            available=stream.available,
            read_only_reason=stream.read_only_reason,
            total=stream.total,
            offers=cls.allocations(stream),
            can_edit=can_edit,
            can_cancel=not busy and stream.dirty,
            can_push=can_edit and stream.dirty,
        )

    @staticmethod
    def allocations(stream: StreamEditor) -> list[OfferAllocationView]:
        result = []
        for offer in sorted(stream.draft.values(), key=lambda o: (not o.active, o.offer_id)):
            old = stream.baseline.get(offer.offer_id)
            status = "active"
            if offer.active and old is None:
                status = "new"
            elif offer.active and old and not old.active:
                status = "restored"
            elif not offer.active:
                status = "removed" if old and old.active else "archived"
            if offer.external_state != "active":
                status = "disabled"
            result.append(
                OfferAllocationView(
                    offer.offer_id,
                    offer.name,
                    offer.weight,
                    offer.active,
                    offer.pinned,
                    offer.external_state,
                    status,
                )
            )
        return result
