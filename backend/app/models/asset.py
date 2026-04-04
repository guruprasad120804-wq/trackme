import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssetType(str, enum.Enum):
    STOCK = "stock"
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"
    BOND = "bond"
    GOLD = "gold"
    FIXED_DEPOSIT = "fixed_deposit"
    NPS = "nps"
    PPF = "ppf"
    CRYPTO = "crypto"
    OTHER = "other"


class Asset(Base):
    """Universal asset master — stocks, MFs, ETFs, bonds, etc."""
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(50), index=True)  # NSE/BSE symbol for stocks
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(20))  # NSE, BSE, NASDAQ
    isin: Mapped[str | None] = mapped_column(String(20), index=True)
    amfi_code: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)  # For MFs
    sector: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)  # Flexible extra fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
