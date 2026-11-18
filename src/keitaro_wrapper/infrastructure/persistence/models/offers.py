from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from keitaro_wrapper.infrastructure.persistence.models.base import Base


class OfferRow(Base):
    __tablename__ = "offer_catalog"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32))
    __table_args__ = (CheckConstraint("id > 0"),)
