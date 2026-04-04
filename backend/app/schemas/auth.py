from pydantic import BaseModel, EmailStr


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None
    is_onboarded: bool
    plan: str = "free"

    model_config = {"from_attributes": True}
