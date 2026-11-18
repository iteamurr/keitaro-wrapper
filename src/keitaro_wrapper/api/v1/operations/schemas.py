from typing import Literal
from uuid import UUID

from pydantic import Field

from keitaro_wrapper.api.common.schemas.base import InSchema, OutSchema, omit_none


class OperationControlIn(InSchema):
    expected_operation_revision: int = Field(ge=0, strict=True)
    decision: Literal["adopt_current", "not_applied"] | None = None
    confirmation: bool = Field(default=False, strict=True)
    note: str = Field(default="", max_length=1000)


class OperationErrorOut(OutSchema):
    code: str
    message: str | None


class OperationResultOut(OutSchema):
    campaign_id: UUID | None = Field(default=None, exclude_if=omit_none)
    operation_id: UUID | None = Field(default=None, exclude_if=omit_none)
    stream_id: int | None = Field(default=None, exclude_if=omit_none)
    keitaro_campaign_id: int | None = Field(default=None, exclude_if=omit_none)
    url: str | None = Field(default=None, exclude_if=omit_none)
    adopted_external_state: bool | None = Field(default=None, exclude_if=omit_none)


class RemoteIDsOut(OutSchema):
    campaign_remote_id: int | None = Field(default=None, exclude_if=omit_none)
    geo_remote_id: int | None = Field(default=None, exclude_if=omit_none)
    fallback_remote_id: int | None = Field(default=None, exclude_if=omit_none)


class OperationOut(OutSchema):
    id: UUID
    kind: Literal["create", "import", "fetch", "edit", "push", "control"]
    parent_operation_id: UUID | None
    campaign_id: UUID
    stream_id: int | None
    status: Literal[
        "running", "succeeded", "failed", "conflict", "partial", "unknown", "manual_review"
    ]
    revision: int = Field(ge=0)
    stage: str | None
    result: OperationResultOut
    error: OperationErrorOut | None
    can_reconcile: bool
    can_resume: bool
    can_resolve: bool
    remote_ids: RemoteIDsOut
