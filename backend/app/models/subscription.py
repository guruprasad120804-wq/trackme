import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRIAL = "trial"
    PAST_DUE = "past_due"


# Feature limits per plan
PLAN_LIMITS = {
    SubscriptionPlan.FREE: {
        "max_portfolios": 1,
        "max_broker_connections": 1,
        "max_alerts": 3,
        "ai_queries_per_day": 5,
        "whatsapp_bot": False,
        "email_scanning": False,
        "export": False,
        "advanced_analytics": False,
    },
    SubscriptionPlan.PRO: {
        "max_portfolios": 5,
        "max_broker_connections": 5,
        "max_alerts": 25,
        "ai_queries_per_day": 50,
        "whatsapp_bot": True,
        "email_scanning": True,
        "export": True,
        "advanced_analytics": True,
    },
    SubscriptionPlan.PREMIUM: {
        "max_portfolios": -1,  # unlimited
        "max_broker_connections": -1,
        "max_alerts": -1,
        "ai_queries_per_day": -1,
        "whatsapp_bot": True,
        "email_scanning": True,
        "export": True,
        "advanced_analytics": True,
    },
}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(SAEnum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    status: Mapped[SubscriptionStatus] = mapped_column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(100))
    razorpay_customer_id: Mapped[str | None] = mapped_column(String(100))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_queries_today: Mapped[int] = mapped_column(Integer, default=0)
    ai_queries_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="subscription")


from app.models.user import User  # noqa: E402
