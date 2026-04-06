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
        "has_cas_password": bool(config.cas_password_encrypted),
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
    from app.auth.google import get_gmail_auth_url
    from app.config import get_settings
    settings = get_settings()

    url = get_gmail_auth_url(
        redirect_uri=f"{settings.frontend_url}/settings/email/callback",
        state=f"email_scan_{user.id}",
    )
    return {"url": url}


@router.post("/email/oauth/callback")
async def email_oauth_callback(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exchange Gmail OAuth code for tokens and store encrypted."""
    from app.auth.google import exchange_code_for_tokens, get_google_user_info
    from app.config import get_settings
    settings = get_settings()

    code = body.get("code")
    redirect_uri = body.get("redirect_uri", f"{settings.frontend_url}/settings/email/callback")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    tokens = await exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)

    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No refresh token received. Please revoke access at myaccount.google.com/permissions and try again.",
        )

    # Get email address from Google profile
    user_info = await get_google_user_info(access_token)

    result = await db.execute(select(EmailConfig).where(EmailConfig.user_id == user.id))
    config = result.scalar_one_or_none()
    if not config:
        config = EmailConfig(user_id=user.id)
        db.add(config)

    config.oauth_token_encrypted = encrypt_value(access_token)
    config.oauth_refresh_token_encrypted = encrypt_value(refresh_token)
    config.email_address = user_info.get("email")
    config.is_active = True

    await db.commit()
    return {"status": "connected", "email": config.email_address}


@router.post("/email/cas-password")
async def save_cas_password(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save encrypted CAS password for email-based import."""
    password = body.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")

    result = await db.execute(select(EmailConfig).where(EmailConfig.user_id == user.id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Connect Gmail first")

    config.cas_password_encrypted = encrypt_value(password)
    await db.commit()
    return {"status": "saved"}


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
