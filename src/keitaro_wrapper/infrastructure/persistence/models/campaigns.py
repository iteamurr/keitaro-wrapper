from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from keitaro_wrapper.infrastructure.persistence.models.base import Base


class CampaignRow(Base):
    __tablename__ = "campaigns"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    remote_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(Text)
    alias: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32))
    revision: Mapped[int] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(Text)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("revision >= 0"),
        CheckConstraint("remote_id IS NULL OR remote_id > 0"),
    )
