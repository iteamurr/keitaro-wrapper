from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from keitaro_wrapper.domain.operations.entity import Operation


@dataclass(frozen=True)
class OperationError:
    code: str
    message: str | None


@dataclass(frozen=True)
class OperationResult:
    campaign_id: UUID | None = None
    operation_id: UUID | None = None
    stream_id: int | None = None
    keitaro_campaign_id: int | None = None
    url: str | None = None
    adopted_external_state: bool | None = None


@dataclass(frozen=True)
class RemoteIDs:
    campaign_remote_id: int | None = None
    geo_remote_id: int | None = None
    fallback_remote_id: int | None = None


@dataclass(frozen=True)
class OperationView:
    id: UUID
    kind: str
    parent_operation_id: UUID | None
    campaign_id: UUID
    stream_id: int | None
    status: str
    revision: int
    stage: str | None
    result: OperationResult
    error: OperationError | None
    can_reconcile: bool
    can_resume: bool
    can_resolve: bool
    remote_ids: RemoteIDs

    @classmethod
    def from_entity(cls, operation: Operation) -> OperationView:
        result = dict(operation.result)
        for name in ("campaign_id", "operation_id"):
            if result.get(name) is not None:
                result[name] = UUID(str(result[name]))
        parent_id = operation.context.get("parent_id") if operation.kind == "control" else None
        remote_ids = {
            name: operation.context[name]
            for name in RemoteIDs.__dataclass_fields__
            if name in operation.context
        }
        return cls(
            id=operation.id,
            kind=operation.kind,
            parent_operation_id=UUID(str(parent_id)) if parent_id else None,
            campaign_id=operation.campaign_id,
            stream_id=operation.stream_id,
            status=operation.status,
            revision=operation.revision,
            stage=operation.context.get("stage"),
            result=OperationResult(**result),
            error=OperationError(operation.error_code, operation.error_message)
            if operation.error_code
            else None,
            can_reconcile=operation.allows_control("reconcile"),
            can_resume=operation.allows_control("resume"),
            can_resolve=operation.allows_control("resolve"),
            remote_ids=RemoteIDs(**remote_ids),
        )
