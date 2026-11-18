from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from keitaro_wrapper.common.types import Document
from keitaro_wrapper.domain.common.errors import DomainError
from keitaro_wrapper.domain.common.snapshot import Snapshot

RESERVED_STATUSES = ("running", "unknown", "manual_review", "partial")
RECOVERABLE_KINDS = ("create", "push", "fetch", "import")
CONTROL_STATUSES = {
    "resume": ("failed", "partial"),
    "reconcile": ("unknown", "manual_review"),
    "resolve": ("unknown", "manual_review"),
}


@dataclass
class Operation:
    id: UUID
    kind: str
    campaign_id: UUID
    fingerprint: str
    payload: Document
    created_at: datetime
    updated_at: datetime
    stream_id: int | None = None
    status: str = "running"
    revision: int = 0
    reserves_campaign: bool = True
    context: Document = field(default_factory=dict)
    result: Document = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None

    def allows_control(self, action: str) -> bool:
        return (
            self.reserves_campaign
            and self.kind in RECOVERABLE_KINDS
            and self.status in CONTROL_STATUSES.get(action, ())
        )

    def assert_control_allowed(self, action: str) -> None:
        if action not in CONTROL_STATUSES:
            raise DomainError("invalid_command", "Неизвестное действие операции.")
        if not self.allows_control(action):
            raise DomainError(
                "operation_busy",
                "Действие недоступно для текущего состояния операции.",
            )

    def transition(
        self,
        status: str,
        result: Document | None = None,
        code: str | None = None,
        message: str | None = None,
        *,
        at: datetime,
    ) -> None:
        if self.status != "running" or status not in {
            "succeeded",
            "failed",
            "conflict",
            "unknown",
            "manual_review",
            "partial",
        }:
            raise DomainError("invalid_transition", "Недопустимый переход состояния операции.")
        if status == "partial" and self.kind != "create":
            raise DomainError(
                "invalid_transition",
                "Частичный результат допустим только для создания кампании.",
            )
        if status in {"unknown", "manual_review"} and (
            not self.reserves_campaign or self.kind not in RECOVERABLE_KINDS
        ):
            raise DomainError("invalid_transition", "Эта операция не поддерживает внешнюю сверку.")
        self.status = status
        if result is not None:
            self.result = result
        self.error_code = code
        self.error_message = message
        self.revision += 1
        self.updated_at = at

    def checkpoint(self, *, at: datetime, **values: object) -> None:
        if self.status != "running":
            raise DomainError(
                "invalid_transition",
                "Изменять этапы можно только у исполняемой операции.",
            )
        self.context = {**self.context, **values}
        self.revision += 1
        self.updated_at = at

    def snapshot(self, name: str) -> Snapshot:
        value = self.context.get(name)
        if not isinstance(value, Snapshot):
            raise DomainError(
                "invalid_checkpoint",
                "Сохранённый снимок операции отсутствует или некорректен.",
            )
        return value

    def __post_init__(self) -> None:
        if self.kind not in {"create", "import", "fetch", "edit", "push", "control"}:
            raise DomainError("invalid_operation", "Неизвестный вид операции.")
        if self.status not in {
            "running",
            "succeeded",
            "failed",
            "conflict",
            "partial",
            "unknown",
            "manual_review",
        }:
            raise DomainError("invalid_operation", "Неизвестное состояние операции.")
        if self.status == "partial" and self.kind != "create":
            raise DomainError(
                "invalid_operation",
                "Частичный результат допустим только для создания кампании.",
            )
        if self.status in {"unknown", "manual_review"} and (
            not self.reserves_campaign or self.kind not in RECOVERABLE_KINDS
        ):
            raise DomainError("invalid_operation", "Эта операция не поддерживает внешнюю сверку.")

    def begin_control(self, action: str, *, at: datetime) -> None:
        self.assert_control_allowed(action)
        self.status = "running"
        self.error_code = None
        self.error_message = None
        self.revision += 1
        self.updated_at = at
