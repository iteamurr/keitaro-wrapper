from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from keitaro_wrapper.common.types import Document
from keitaro_wrapper.infrastructure.persistence.models.base import Base


class StreamRow(Base):
    __tablename__ = "stream_editors"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean)
    read_only_reason: Mapped[str | None] = mapped_column(Text)
    remote_baseline: Mapped[Document] = mapped_column(JSONB)
    editor_baseline: Mapped[Document] = mapped_column(JSONB)
    editor_draft: Mapped[Document] = mapped_column(JSONB)
    __table_args__ = (
        CheckConstraint("id > 0 AND revision >= 0"),
        CheckConstraint("jsonb_typeof(remote_baseline) = 'object'"),
        CheckConstraint("jsonb_typeof(editor_baseline) = 'object'"),
        CheckConstraint("jsonb_typeof(editor_draft) = 'object'"),
    )
