import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="user", uselist=False)
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_conversations: Mapped[list["ChatConversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    broker_connections: Mapped[list["BrokerConnection"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    email_config: Mapped["EmailConfig | None"] = relationship(back_populates="user", uselist=False)
    whatsapp_config: Mapped["WhatsAppConfig | None"] = relationship(back_populates="user", uselist=False)
    mf_connection: Mapped["MFConnection | None"] = relationship(back_populates="user", uselist=False)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    insurance_policies: Mapped[list["InsurancePolicy"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    import_logs: Mapped[list["ImportLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# Deferred imports for type checking
from app.models.portfolio import Portfolio  # noqa: E402
from app.models.subscription import Subscription  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.chat import ChatConversation  # noqa: E402
from app.models.broker import BrokerConnection  # noqa: E402
from app.models.import_log import EmailConfig, ImportLog  # noqa: E402
from app.models.whatsapp import WhatsAppConfig  # noqa: E402
from app.models.mf_connection import MFConnection  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.insurance import InsurancePolicy  # noqa: E402
