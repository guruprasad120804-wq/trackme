import enum
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import ForeignKey, DateTime, Numeric, String, Enum, Date, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    SIP = "sip"
    DIVIDEND = "dividend"
    DIVIDEND_REINVEST = "dividend_reinvest"
    SWITCH_IN = "switch_in"
    SWITCH_OUT = "switch_out"
    BONUS = "bonus"
    SPLIT = "split"
    RIGHTS = "rights"
    REDEMPTION = "redemption"
    STAMP_DUTY = "stamp_duty"
    STT = "stt"
    TDS = "tds"
    OTHER = "other"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    holding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("holdings.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    settlement_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    charges: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    stamp_duty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))  # For MF transactions
    source: Mapped[str | None] = mapped_column(String(50))  # "broker_api", "cas_import", "email", "manual"
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    holding: Mapped["Holding"] = relationship(back_populates="transactions")

    __table_args__ = (
        UniqueConstraint(
            "holding_id", "trade_date", "type", "amount", "quantity",
            name="uq_transaction_dedup"
        ),
    )


from app.models.holding import Holding  # noqa: E402
