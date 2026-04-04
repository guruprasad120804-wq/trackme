import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, JSON, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class BrokerType(str, enum.Enum):
    ZERODHA = "zerodha"
    GROWW = "groww"
    UPSTOX = "upstox"
    ANGEL_ONE = "angel_one"
    ICICI_DIRECT = "icici_direct"
    HDFC_SECURITIES = "hdfc_securities"
    KOTAK_SECURITIES = "kotak_securities"
    FYERS = "fyers"
    FIVE_PAISA = "five_paisa"
    DHAN = "dhan"
    CAMS = "cams"
    KFINTECH = "kfintech"
    OTHER = "other"


class ConnectionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class Broker(Base):
    __tablename__ = "brokers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[BrokerType] = mapped_column(SAEnum(BrokerType), nullable=False, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)
    supports_stocks: Mapped[bool] = mapped_column(default=False)
    supports_mf: Mapped[bool] = mapped_column(default=False)
    supports_etf: Mapped[bool] = mapped_column(default=False)
    api_docs_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrokerConnection(Base):
    __tablename__ = "broker_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    status: Mapped[ConnectionStatus] = mapped_column(SAEnum(ConnectionStatus), default=ConnectionStatus.ACTIVE)
    credentials_encrypted: Mapped[str | None] = mapped_column(String(2000))  # Fernet encrypted
    access_token_encrypted: Mapped[str | None] = mapped_column(String(2000))
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String(2000))
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_error: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="broker_connections")
    broker: Mapped["Broker"] = relationship()


from app.models.user import User  # noqa: E402
