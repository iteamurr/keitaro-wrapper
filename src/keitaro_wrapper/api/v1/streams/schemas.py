from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from keitaro_wrapper.api.common.schemas.base import OutSchema
from keitaro_wrapper.api.common.schemas.revisions import RevisionIn


class StreamRevisionIn(RevisionIn):
    pass


class StreamAddOfferIn(RevisionIn):
    offer_id: int = Field(gt=0, strict=True)


class StreamPinOfferIn(RevisionIn):
    pinned: bool = Field(strict=True)
    weight: int | None = Field(default=None, ge=1, le=100, strict=True)

    @model_validator(mode="after")
    def validate_weight(self) -> StreamPinOfferIn:
        if self.pinned and self.weight is None:
            raise ValueError("Pinned weight is required")
        return self


class OfferAllocationOut(OutSchema):
    offer_id: int
    name: str
    weight: int
    active: bool
    pinned: bool
    external_state: str
    status: Literal["active", "new", "restored", "removed", "archived", "disabled"]


class StreamOut(OutSchema):
    id: int
    name: str
    revision: int
    dirty: bool
    available: bool
    read_only_reason: str | None
    total: int
    offers: list[OfferAllocationOut]
    can_edit: bool
    can_cancel: bool
    can_push: bool
