import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # "cas_upload", "email_scan", "broker_sync", "manual"
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending", "processing", "completed", "failed"
    file_name: Mapped[str | None] = mapped_column(String(255))
    schemes_added: Mapped[int] = mapped_column(Integer, default=0)
    transactions_added: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="import_logs")


class EmailConfig(Base):
    __tablename__ = "email_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    email_address: Mapped[str | None] = mapped_column(String(255))
    oauth_token_encrypted: Mapped[str | None] = mapped_column(String(2000))
    oauth_refresh_token_encrypted: Mapped[str | None] = mapped_column(String(2000))
    cas_password_encrypted: Mapped[str | None] = mapped_column(String(500))
    last_scanned: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="email_config")


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="success")
    error_message: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_processed_email_user_msg"),
    )
