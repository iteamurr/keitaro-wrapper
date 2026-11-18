from pydantic import Field

from keitaro_wrapper.api.common.schemas.base import OutSchema
from keitaro_wrapper.api.common.schemas.pagination import PaginationIn


class OfferSearchIn(PaginationIn):
    q: str = Field(default="", max_length=200)


class OfferOut(OutSchema):
    id: int
    name: str
