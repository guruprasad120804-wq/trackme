"""Mutual Fund import via PAN + OTP (aggregator API)."""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.mf_connection import MFConnection
from app.models.import_log import ImportLog
from app.services.mf_aggregator import aggregator_client
from app.services.mf_import import import_mf_portfolio
from app.utils.dependencies import get_current_user

router = APIRouter()

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


# --- Request / Response schemas ---

class StartRequest(BaseModel):
    pan: str

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        v = v.strip().upper()
        if not PAN_REGEX.match(v):
            raise ValueError("Invalid PAN format. Expected: ABCDE1234F")
        return v


class VerifyRequest(BaseModel):
    session_id: str
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) < 4 or len(v) > 8:
            raise ValueError("OTP must be 4-8 digits")
        return v


# --- Routes ---

@router.post("/connect/start")
async def start_mf_connect(
    body: StartRequest,
    user: User = Depends(get_current_user),
):
    """Initiate PAN-based MF connection — sends OTP to registered mobile."""
    result = await aggregator_client.start_session(body.pan)
    return {
        "session_id": result.get("session_id"),
        "message": result.get("message", "OTP sent to registered mobile number"),
    }


@router.post("/connect/verify")
async def verify_mf_connect(
    body: VerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP, establish connection, and import portfolio data."""
    # Verify OTP with aggregator
    verify_result = await aggregator_client.verify_otp(body.session_id, body.otp)
    consent_id = verify_result.get("consent_id")
    if not consent_id:
        raise HTTPException(status_code=400, detail="Verification failed — no consent received")

    # Fetch portfolio data
    portfolio_data = await aggregator_client.fetch_portfolio(consent_id)

    # Import into database
    import_stats = await import_mf_portfolio(str(user.id), portfolio_data, db)

    # Create or update MFConnection
    result = await db.execute(
        select(MFConnection).where(MFConnection.user_id == user.id)
    )
    mf_conn = result.scalar_one_or_none()

    # We need the PAN from the start request — extract from session or portfolio data
    pan = portfolio_data.get("folios", [{}])[0].get("pan", "") if portfolio_data.get("folios") else ""

    if mf_conn:
        mf_conn.consent_id = consent_id
        mf_conn.status = "active"
        mf_conn.last_synced_at = datetime.now(timezone.utc)
        if pan:
            mf_conn.pan = pan
    else:
        mf_conn = MFConnection(
            user_id=user.id,
            pan=pan,
            consent_id=consent_id,
            status="active",
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(mf_conn)

    # Create import log
    import_log = ImportLog(
        user_id=user.id,
        source="mf_aggregator",
        status="completed",
        schemes_added=import_stats["schemes_added"],
        transactions_added=import_stats["transactions_added"],
        errors=len(import_stats["errors"]),
        error_details="; ".join(import_stats["errors"]) if import_stats["errors"] else None,
        summary_json=import_stats,
    )
    db.add(import_log)
    await db.commit()

    return {
        "status": "connected",
        "schemes_added": import_stats["schemes_added"],
        "transactions_added": import_stats["transactions_added"],
        "holdings_updated": import_stats["holdings_updated"],
        "folios_added": import_stats["folios_added"],
        "errors": import_stats["errors"],
    }


@router.post("/sync")
async def sync_mf_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-sync portfolio data using existing aggregator connection."""
    result = await db.execute(
        select(MFConnection).where(MFConnection.user_id == user.id)
    )
    mf_conn = result.scalar_one_or_none()

    if not mf_conn:
        raise HTTPException(status_code=404, detail="No MF connection found. Connect with PAN + OTP first.")
    if mf_conn.status == "expired":
        raise HTTPException(status_code=400, detail="Connection expired. Please reconnect with PAN + OTP.")
    if mf_conn.status == "revoked":
        raise HTTPException(status_code=400, detail="Connection revoked. Please reconnect with PAN + OTP.")

    # Fetch latest portfolio
    portfolio_data = await aggregator_client.fetch_portfolio(mf_conn.consent_id)

    # Import (idempotent — dedup constraint prevents duplicate transactions)
    import_stats = await import_mf_portfolio(str(user.id), portfolio_data, db)

    # Update sync timestamp
    mf_conn.last_synced_at = datetime.now(timezone.utc)

    # Create import log
    import_log = ImportLog(
        user_id=user.id,
        source="mf_sync",
        status="completed",
        schemes_added=import_stats["schemes_added"],
        transactions_added=import_stats["transactions_added"],
        errors=len(import_stats["errors"]),
        error_details="; ".join(import_stats["errors"]) if import_stats["errors"] else None,
        summary_json=import_stats,
    )
    db.add(import_log)
    await db.commit()

    return {
        "status": "synced",
        "schemes_added": import_stats["schemes_added"],
        "transactions_added": import_stats["transactions_added"],
        "holdings_updated": import_stats["holdings_updated"],
        "last_synced_at": mf_conn.last_synced_at.isoformat(),
    }


@router.get("/connection")
async def get_mf_connection(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current MF connection status."""
    result = await db.execute(
        select(MFConnection).where(MFConnection.user_id == user.id)
    )
    mf_conn = result.scalar_one_or_none()

    if not mf_conn:
        return {"connected": False}

    # Mask PAN: ABCDE1234F → XXXXX1234X
    masked_pan = ""
    if mf_conn.pan and len(mf_conn.pan) == 10:
        masked_pan = f"XXXXX{mf_conn.pan[5:9]}X"

    return {
        "connected": True,
        "status": mf_conn.status,
        "pan": masked_pan,
        "last_synced_at": mf_conn.last_synced_at.isoformat() if mf_conn.last_synced_at else None,
        "created_at": mf_conn.created_at.isoformat(),
    }
