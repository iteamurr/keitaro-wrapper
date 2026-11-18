from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from keitaro_wrapper.infrastructure.persistence.models.base import Base


class IntegrationRow(Base):
    __tablename__ = "integration_binding"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(Text)
    catalog_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("id = 1"),)
