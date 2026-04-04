import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, DateTime, Numeric, String, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Holding(Base):
    """A user's position in a specific asset within a portfolio."""
    __tablename__ = "holdings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True)
    broker_connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("broker_connections.id"))

    # For mutual funds — folio-level tracking
    folio_number: Mapped[str | None] = mapped_column(String(50))

    # Position data
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    total_invested: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    day_change: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    day_change_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    total_gain: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    total_gain_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    xirr: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship()
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="holding", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", "folio_number", name="uq_holding_portfolio_asset_folio"),
    )


from app.models.portfolio import Portfolio  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402
