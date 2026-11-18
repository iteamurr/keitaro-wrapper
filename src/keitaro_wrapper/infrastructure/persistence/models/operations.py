from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from keitaro_wrapper.common.types import Document
from keitaro_wrapper.infrastructure.persistence.models.base import Base


class OperationRow(Base):
    __tablename__ = "operations"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id"), index=True)
    stream_id: Mapped[int | None] = mapped_column(ForeignKey("stream_editors.id"))
    fingerprint: Mapped[str] = mapped_column(String(64))
    payload: Mapped[Document] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24))
    revision: Mapped[int] = mapped_column(Integer)
    reserves_campaign: Mapped[bool] = mapped_column(Boolean)
    context: Mapped[Document] = mapped_column(JSONB)
    result: Mapped[Document] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("revision >= 0"),
        Index(
            "uq_campaign_reservation",
            "campaign_id",
            unique=True,
            postgresql_where=text(
                "reserves_campaign AND status IN ('running', 'unknown', 'manual_review', 'partial')"
            ),
        ),
    )


class AttemptRow(Base):
    __tablename__ = "operation_attempts"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    operation_id: Mapped[UUID] = mapped_column(ForeignKey("operations.id"))
    number: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(40))
    expected: Mapped[Document] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("operation_id", "number"), CheckConstraint("number > 0"))
