import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Numeric, Date, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FundHouse(Base):
    __tablename__ = "fund_houses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(String(500))


class Scheme(Base):
    """Mutual fund scheme details — linked to the universal Asset table."""
    __tablename__ = "schemes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, unique=True)
    fund_house_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fund_houses.id"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    sub_category: Mapped[str | None] = mapped_column(String(100))
    plan_type: Mapped[str | None] = mapped_column(String(20))  # Direct, Regular
    option: Mapped[str | None] = mapped_column(String(20))  # Growth, IDCW
    rta: Mapped[str | None] = mapped_column(String(20))  # CAMS, KFintech
    rta_code: Mapped[str | None] = mapped_column(String(20))


class Folio(Base):
    """User's folio for a specific fund house."""
    __tablename__ = "folios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fund_house_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fund_houses.id"), nullable=False)
    folio_number: Mapped[str] = mapped_column(String(50), nullable=False)
    pan: Mapped[str | None] = mapped_column(String(10))
    registrar: Mapped[str | None] = mapped_column(String(20))

    __table_args__ = (
        UniqueConstraint("user_id", "folio_number", name="uq_folio_user_number"),
    )


class NavHistory(Base):
    __tablename__ = "nav_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schemes.id"), nullable=False, index=True)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    __table_args__ = (
        UniqueConstraint("scheme_id", "nav_date", name="uq_nav_history_scheme_date"),
    )
