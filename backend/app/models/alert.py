import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Numeric, Boolean, Enum as SAEnum, JSON, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertCondition(str, enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    GAIN_PCT_ABOVE = "gain_pct_above"
    LOSS_PCT_ABOVE = "loss_pct_above"
    PORTFOLIO_VALUE_ABOVE = "portfolio_value_above"
    PORTFOLIO_VALUE_BELOW = "portfolio_value_below"
    DAY_CHANGE_PCT = "day_change_pct"
    SIP_REMINDER = "sip_reminder"
    CUSTOM = "custom"


class AlertChannel(str, enum.Enum):
    PUSH = "push"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"))
    condition: Mapped[AlertCondition] = mapped_column(SAEnum(AlertCondition), nullable=False)
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=["push"])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)  # Fire once vs recurring
    rule_json: Mapped[dict | None] = mapped_column(JSON)  # Custom rule definitions
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="alerts")
    history: Mapped[list["AlertHistory"]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    value_at_trigger: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    channel_used: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(String(500))

    alert: Mapped["Alert"] = relationship(back_populates="history")


from app.models.user import User  # noqa: E402
