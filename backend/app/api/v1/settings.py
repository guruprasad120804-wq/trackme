from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.import_log import EmailConfig
from app.models.whatsapp import WhatsAppConfig
from app.utils.dependencies import get_current_user
from app.utils.security import encrypt_value

router = APIRouter()


@router.get("/email")
async def get_email_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailConfig).where(EmailConfig.user_id == user.id))
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False}

    return {
        "configured": True,
        "email_address": config.email_address,
        "is_active": config.is_active,
        "last_scanned": str(config.last_scanned) if config.last_scanned else None,
    }


@router.post("/email")
async def save_email_config(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailConfig).where(EmailConfig.user_id == user.id))
    config = result.scalar_one_or_none()

    cas_password = body.get("cas_password")
    if not config:
        config = EmailConfig(user_id=user.id)
        db.add(config)

    if cas_password:
        config.cas_password_encrypted = encrypt_value(cas_password)
    config.is_active = body.get("is_active", True)

    await db.commit()
    return {"status": "saved"}


@router.get("/email/oauth/authorize")
async def get_email_oauth_url(
    user: User = Depends(get_current_user),
):
    """Get Google OAuth URL for Gmail access (email scanning)."""
    from app.auth.google import get_google_auth_url
    from app.config import get_settings
    settings = get_settings()

    url = get_google_auth_url(
        redirect_uri=f"{settings.frontend_url}/settings/email/callback",
        state=f"email_scan_{user.id}",
    )
    return {"url": url}


@router.get("/whatsapp")
async def get_whatsapp_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WhatsAppConfig).where(WhatsAppConfig.user_id == user.id))
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False}

    return {
        "configured": True,
        "phone_number": config.phone_number,
        "is_verified": config.is_verified,
        "is_active": config.is_active,
    }


@router.post("/whatsapp")
async def save_whatsapp_config(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    phone = body.get("phone_number")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required")

    result = await db.execute(select(WhatsAppConfig).where(WhatsAppConfig.user_id == user.id))
    config = result.scalar_one_or_none()

    if not config:
        config = WhatsAppConfig(user_id=user.id, phone_number=phone)
        db.add(config)
    else:
        config.phone_number = phone

    await db.commit()
    return {"status": "saved"}


@router.patch("/profile")
async def update_profile(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if "name" in body:
        user.name = body["name"]
    if "is_onboarded" in body:
        user.is_onboarded = body["is_onboarded"]
    await db.commit()
    return {"status": "updated"}
