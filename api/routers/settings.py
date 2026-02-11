"""Settings router - global platform settings, API key testing, backup/restore."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class SettingsResponse(BaseModel):
    """Full platform settings."""

    # Exchange
    exchange: str = "binance"
    exchange_api_key_set: bool = False
    exchange_api_secret_set: bool = False

    # Telegram
    telegram_enabled: bool = False
    telegram_bot_token_set: bool = False
    telegram_chat_id: str = ""

    # AI Agent
    openrouter_api_key_set: bool = False
    openrouter_model: str = "anthropic/claude-sonnet-4"

    # General
    timezone: str = "UTC"
    language: str = "fr"
    theme: str = "dark"


class SettingsUpdateRequest(BaseModel):
    """Body for PUT /settings/ (partial update).

    Sensitive fields (API keys) are write-only: they appear as booleans in
    SettingsResponse but are accepted as strings here.
    """

    # Exchange
    exchange: str | None = None
    exchange_api_key: str | None = Field(None, description="Write-only")
    exchange_api_secret: str | None = Field(None, description="Write-only")

    # Telegram
    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = Field(None, description="Write-only")
    telegram_chat_id: str | None = None

    # AI Agent
    openrouter_api_key: str | None = Field(None, description="Write-only")
    openrouter_model: str | None = None

    # General
    timezone: str | None = None
    language: str | None = None
    theme: str | None = None


class TestExchangeRequest(BaseModel):
    """Body for POST /settings/test-exchange."""

    api_key: str
    api_secret: str
    exchange: str = "binance"


class TestTelegramRequest(BaseModel):
    """Body for POST /settings/test-telegram."""

    bot_token: str
    chat_id: str


# ---------------------------------------------------------------------------
# Read / Update
# ---------------------------------------------------------------------------

@router.get("/", response_model=SettingsResponse)
async def get_settings(
    current_user: dict = Depends(get_current_active_user),
):
    """Get all platform settings (sensitive fields masked)."""
    # TODO: read from config / DB
    return SettingsResponse()


@router.put("/", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update platform settings."""
    # TODO: validate, encrypt secrets, write to config / DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings update not yet wired",
    )


# ---------------------------------------------------------------------------
# Test connections
# ---------------------------------------------------------------------------

@router.post("/test-exchange", response_model=SuccessResponse)
async def test_exchange(
    body: TestExchangeRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Test exchange API connectivity with provided credentials."""
    # TODO: attempt a read-only API call (e.g. get account info)
    return SuccessResponse(message="Exchange connection test not yet implemented")


@router.post("/test-telegram", response_model=SuccessResponse)
async def test_telegram(
    body: TestTelegramRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Send a test message to Telegram to verify bot token and chat ID."""
    # TODO: send "Test OK" message via Telegram API
    return SuccessResponse(message="Telegram test not yet implemented")


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------

@router.post("/backup")
async def backup_config(
    current_user: dict = Depends(get_current_active_user),
):
    """Export all configuration as a downloadable JSON file.

    Sensitive fields (API keys) are excluded.
    """
    # TODO: build config export
    return {"config": {}, "exported_at": ""}


@router.post("/restore", response_model=SuccessResponse)
async def restore_config(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Import configuration from a previously exported JSON file."""
    # TODO: validate and apply config
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Config restore not yet implemented",
    )
