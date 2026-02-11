"""Authentication router - register, login, token refresh, profile."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from api.auth.password import hash_password, verify_password
from api.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UpdateProfileRequest,
    UserResponse,
)
from api.schemas.common import SuccessResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest):
    """Create a new user account."""
    # TODO: check if email already exists in DB
    # TODO: hash password and insert user into DB
    hashed = hash_password(body.password)  # noqa: F841
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User registration not yet wired to the database",
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate a user and return JWT tokens."""
    # TODO: look up user by email
    # TODO: verify_password(body.password, user.hashed_password)
    # TODO: return tokens + user
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Login not yet wired to the database",
    )


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest):
    """Exchange a valid refresh token for a new token pair."""
    payload = verify_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )
    sub = payload["sub"]
    access = create_access_token({"sub": sub})
    refresh_tok = create_refresh_token({"sub": sub})
    return TokenPair(
        access_token=access,
        refresh_token=refresh_tok,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_active_user)):
    """Return the authenticated user's profile."""
    # TODO: query full user from DB by current_user["sub"]
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Profile retrieval not yet wired to the database",
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update the authenticated user's profile."""
    # TODO: update user fields in DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Profile update not yet wired to the database",
    )


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Change the authenticated user's password."""
    # TODO: verify current password, hash new password, update DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password change not yet wired to the database",
    )
