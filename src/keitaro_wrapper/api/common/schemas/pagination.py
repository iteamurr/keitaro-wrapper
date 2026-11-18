from pydantic import BaseModel, Field

from keitaro_wrapper.api.common.schemas.base import OutSchema


class PaginationIn(BaseModel):
    # Pagination is reusable alongside other query parameters, such as offer search.
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PageOut[T](OutSchema):
    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool
