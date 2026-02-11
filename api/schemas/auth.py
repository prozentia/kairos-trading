"""Authentication & user schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str = Field(..., min_length=3, max_length=64)


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Body for POST /auth/change-password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    """Body for PUT /auth/me."""

    username: str | None = Field(None, min_length=3, max_length=64)
    email: EmailStr | None = None
    telegram_chat_id: str | None = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class TokenPair(BaseModel):
    """Access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class LoginResponse(BaseModel):
    """Response for POST /auth/login."""

    tokens: TokenPair
    user: "UserResponse"


class UserResponse(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    telegram_chat_id: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None
