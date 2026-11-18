from datetime import datetime
from uuid import UUID

import pycountry
from pydantic import Field, field_validator

from keitaro_wrapper.api.common.schemas.base import InSchema, OutSchema
from keitaro_wrapper.api.common.schemas.pagination import PaginationIn
from keitaro_wrapper.api.common.schemas.revisions import RevisionIn
from keitaro_wrapper.api.v1.operations.schemas import OperationOut
from keitaro_wrapper.api.v1.streams.schemas import StreamOut


class CampaignCreateIn(InSchema):
    name: str = Field(min_length=1, max_length=200)
    country_code: str = Field(min_length=2, max_length=2)
    offer_id: int = Field(gt=0, strict=True)

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str) -> str:
        value = value.upper()
        if pycountry.countries.get(alpha_2=value) is None:
            raise ValueError("Unknown country")
        return value


class CampaignImportIn(InSchema):
    keitaro_campaign_id: int = Field(gt=0, strict=True)


class CampaignFetchIn(RevisionIn):
    pass


class CampaignListIn(PaginationIn):
    limit: int = Field(default=100, ge=1, le=100)


class CampaignSummaryOut(OutSchema):
    id: UUID
    keitaro_id: int | None
    name: str
    state: str
    revision: int


class CampaignOut(CampaignSummaryOut):
    url: str | None
    busy: bool
    can_fetch: bool
    last_fetched_at: datetime | None
    streams: list[StreamOut]
    operations: list[OperationOut]
