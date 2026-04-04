from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.google import exchange_code_for_tokens, get_google_user_info
from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.portfolio import Portfolio
from app.schemas.auth import GoogleAuthRequest, TokenResponse, UserResponse, RefreshTokenRequest
from app.utils.security import create_access_token, create_refresh_token, decode_token

router = APIRouter()


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate via Google OAuth. Creates user on first login."""
    tokens = await exchange_code_for_tokens(body.code, body.redirect_uri)
    google_user = await get_google_user_info(tokens["access_token"])

    google_id = google_user["id"]
    email = google_user["email"]
    name = google_user.get("name", email.split("@")[0])
    avatar = google_user.get("picture")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email, name=name, avatar_url=avatar, google_id=google_id)
        db.add(user)
        await db.flush()

        # Create default subscription (free)
        sub = Subscription(user_id=user.id, plan=SubscriptionPlan.FREE, status=SubscriptionStatus.ACTIVE)
        db.add(sub)

        # Create default portfolio
        portfolio = Portfolio(user_id=user.id, name="My Portfolio", is_default=True)
        db.add(portfolio)

        await db.commit()
        await db.refresh(user)
    else:
        # Update profile info from Google
        user.name = name
        user.avatar_url = avatar
        await db.commit()

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_onboarded=user.is_onboarded,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_onboarded=user.is_onboarded,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(__import__("app.utils.dependencies", fromlist=["get_current_user"]).get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_onboarded=user.is_onboarded,
    )
