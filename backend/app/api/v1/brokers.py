"""Broker OAuth connect + holdings sync endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.user import User
from app.models.broker import Broker, BrokerConnection, BrokerType, ConnectionStatus
from app.models.subscription import PLAN_LIMITS
from app.utils.dependencies import get_current_user
from app.utils.security import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Broker info for frontend ---

BROKER_INFO = {
    BrokerType.ZERODHA: {"name": "Zerodha", "logo": "/brokers/zerodha.png"},
    BrokerType.UPSTOX: {"name": "Upstox", "logo": "/brokers/upstox.png"},
    BrokerType.FYERS: {"name": "Fyers", "logo": "/brokers/fyers.png"},
    BrokerType.ANGEL_ONE: {"name": "Angel One", "logo": "/brokers/angelone.png"},
    BrokerType.FIVE_PAISA: {"name": "5paisa", "logo": "/brokers/5paisa.png"},
    BrokerType.DHAN: {"name": "Dhan", "logo": "/brokers/dhan.png"},
}


@router.get("/available")
async def get_available_brokers(user: User = Depends(get_current_user)):
    """List brokers that have API credentials configured."""
    from app.integrations.brokers.registry import get_configured_broker_types, get_adapter

    configured = get_configured_broker_types()
    brokers = []
    for bt in configured:
        adapter = get_adapter(bt)
        info = BROKER_INFO.get(bt, {"name": bt.value, "logo": None})
        brokers.append({
            "type": bt.value,
            "name": info["name"],
            "logo": info["logo"],
            "auth_type": adapter.auth_type,
        })
    return brokers


@router.get("/connections")
async def get_broker_connections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's connected brokers."""
    result = await db.execute(
        select(BrokerConnection)
        .options(joinedload(BrokerConnection.broker))
        .where(BrokerConnection.user_id == user.id)
        .order_by(BrokerConnection.created_at.desc())
    )
    connections = result.unique().scalars().all()

    return [
        {
            "id": str(c.id),
            "broker_type": c.broker.type.value,
            "broker_name": BROKER_INFO.get(c.broker.type, {}).get("name", c.broker.name),
            "status": c.status.value,
            "last_synced": c.last_synced.isoformat() if c.last_synced else None,
            "sync_error": c.sync_error,
            "created_at": c.created_at.isoformat(),
        }
        for c in connections
    ]


@router.get("/{broker_type}/oauth/authorize")
async def get_broker_oauth_url(
    broker_type: str,
    user: User = Depends(get_current_user),
):
    """Get OAuth authorization URL for a broker."""
    from app.integrations.brokers.registry import get_adapter
    from app.config import get_settings

    try:
        bt = BrokerType(broker_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown broker type: {broker_type}")

    adapter = get_adapter(bt)
    if not adapter.is_configured():
        raise HTTPException(status_code=400, detail=f"{adapter.broker_name} is not configured")
    if adapter.auth_type != "oauth":
        raise HTTPException(status_code=400, detail=f"{adapter.broker_name} uses credentials form, not OAuth")

    settings = get_settings()
    redirect_uri = f"{settings.frontend_url}/settings/brokers/callback"
    state = broker_type

    url = adapter.get_auth_url(redirect_uri, state)
    return {"url": url, "broker_type": broker_type}


@router.post("/{broker_type}/oauth/callback")
async def broker_oauth_callback(
    broker_type: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for tokens and store connection."""
    from app.integrations.brokers.registry import get_adapter
    from app.config import get_settings

    try:
        bt = BrokerType(broker_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown broker type: {broker_type}")

    # Check subscription limits
    await _check_connection_limit(user, db)

    adapter = get_adapter(bt)
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    settings = get_settings()
    redirect_uri = body.get("redirect_uri", f"{settings.frontend_url}/settings/brokers/callback")

    try:
        tokens = await adapter.exchange_token(code, redirect_uri)
    except Exception as e:
        logger.error(f"Broker token exchange failed for {broker_type}: {e}")
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    # Find or create broker record
    broker = await _get_or_create_broker(bt, db)

    # Find existing connection or create new
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker_id == broker.id,
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        conn = BrokerConnection(user_id=user.id, broker_id=broker.id)
        db.add(conn)

    conn.access_token_encrypted = encrypt_value(access_token)
    if tokens.get("refresh_token"):
        conn.refresh_token_encrypted = encrypt_value(tokens["refresh_token"])
    if tokens.get("expires_in"):
        from datetime import timedelta
        conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
    conn.status = ConnectionStatus.ACTIVE
    conn.sync_error = None
    if tokens.get("extra"):
        conn.metadata_json = tokens["extra"]

    await db.commit()
    return {"status": "connected", "broker_type": broker_type, "connection_id": str(conn.id)}


@router.post("/{broker_type}/credentials")
async def broker_credentials_auth(
    broker_type: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Angel One style: authenticate with credentials (client code + PIN + TOTP)."""
    from app.integrations.brokers.registry import get_adapter
    import json

    try:
        bt = BrokerType(broker_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown broker type: {broker_type}")

    await _check_connection_limit(user, db)

    adapter = get_adapter(bt)
    if adapter.auth_type != "credentials_form":
        raise HTTPException(status_code=400, detail=f"{adapter.broker_name} uses OAuth, not credentials")

    try:
        tokens = await adapter.exchange_token(json.dumps(body), "")
    except Exception as e:
        logger.error(f"Broker credentials auth failed for {broker_type}: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Authentication failed — no token received")

    broker = await _get_or_create_broker(bt, db)

    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user.id,
            BrokerConnection.broker_id == broker.id,
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        conn = BrokerConnection(user_id=user.id, broker_id=broker.id)
        db.add(conn)

    conn.access_token_encrypted = encrypt_value(access_token)
    if tokens.get("refresh_token"):
        conn.refresh_token_encrypted = encrypt_value(tokens["refresh_token"])
    if tokens.get("expires_in"):
        from datetime import timedelta
        conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
    conn.status = ConnectionStatus.ACTIVE
    conn.sync_error = None
    if tokens.get("extra"):
        conn.metadata_json = tokens["extra"]

    await db.commit()
    return {"status": "connected", "broker_type": broker_type, "connection_id": str(conn.id)}


@router.post("/{connection_id}/sync")
async def sync_broker_holdings(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch and sync holdings from a connected broker."""
    from app.integrations.brokers.registry import get_adapter
    from app.services.broker_sync import sync_holdings_from_broker
    import uuid

    result = await db.execute(
        select(BrokerConnection)
        .options(joinedload(BrokerConnection.broker))
        .where(BrokerConnection.id == uuid.UUID(connection_id), BrokerConnection.user_id == user.id)
    )
    conn = result.unique().scalar_one_or_none()

    if not conn:
        raise HTTPException(status_code=404, detail="Broker connection not found")
    if conn.status == ConnectionStatus.REVOKED:
        raise HTTPException(status_code=400, detail="Connection revoked. Please reconnect.")

    if not conn.access_token_encrypted:
        raise HTTPException(status_code=400, detail="No access token. Please reconnect.")

    access_token = decrypt_value(conn.access_token_encrypted)
    adapter = get_adapter(conn.broker.type)

    try:
        holdings = await adapter.fetch_holdings(access_token)
    except Exception as e:
        conn.status = ConnectionStatus.ERROR
        conn.sync_error = str(e)[:500]
        await db.commit()
        logger.error(f"Broker sync failed for {conn.broker.type.value}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch holdings: {str(e)}")

    stats = await sync_holdings_from_broker(
        user_id=str(user.id),
        broker_connection_id=connection_id,
        holdings_data=holdings,
        db=db,
    )

    conn.last_synced = datetime.now(timezone.utc)
    conn.sync_error = None
    conn.status = ConnectionStatus.ACTIVE
    await db.commit()

    return {
        "status": "synced",
        "holdings_synced": stats["holdings_synced"],
        "assets_created": stats["assets_created"],
        "errors": stats["errors"],
    }


@router.delete("/{connection_id}")
async def disconnect_broker(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect a broker (revoke and delete)."""
    import uuid

    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == uuid.UUID(connection_id),
            BrokerConnection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        raise HTTPException(status_code=404, detail="Broker connection not found")

    await db.delete(conn)
    await db.commit()
    return {"status": "disconnected"}


# --- Helpers ---

async def _get_or_create_broker(bt: BrokerType, db: AsyncSession) -> Broker:
    result = await db.execute(select(Broker).where(Broker.type == bt))
    broker = result.scalar_one_or_none()
    if not broker:
        info = BROKER_INFO.get(bt, {"name": bt.value, "logo": None})
        broker = Broker(
            name=info["name"],
            type=bt,
            supports_stocks=True,
            supports_etf=True,
            logo_url=info["logo"],
        )
        db.add(broker)
        await db.flush()
    return broker


async def _check_connection_limit(user: User, db: AsyncSession):
    """Check if user has reached their subscription's broker connection limit."""
    result = await db.execute(
        select(func.count(BrokerConnection.id)).where(BrokerConnection.user_id == user.id)
    )
    count = result.scalar() or 0

    plan = user.subscription_plan.value if user.subscription_plan else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS.get("free", {}))
    max_connections = limits.get("max_broker_connections", 1)

    if max_connections != -1 and count >= max_connections:
        raise HTTPException(
            status_code=403,
            detail=f"You've reached the maximum of {max_connections} broker connection(s) on your {plan} plan. Upgrade to connect more brokers.",
        )
