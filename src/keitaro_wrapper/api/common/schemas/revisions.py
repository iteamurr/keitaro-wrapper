from pydantic import Field

from keitaro_wrapper.api.common.schemas.base import InSchema


class RevisionIn(InSchema):
    expected_revision: int = Field(ge=0, strict=True)
