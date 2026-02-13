"""Settings router - global platform settings, API key testing, backup/restore."""

import json
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse

import httpx

router = APIRouter()

# In-memory settings store (can be upgraded to DB / encrypted vault)
_settings_store: dict = {}


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
# Helpers
# ---------------------------------------------------------------------------

def _build_response() -> SettingsResponse:
    """Build settings response from the in-memory store."""
    return SettingsResponse(
        exchange=_settings_store.get("exchange", "binance"),
        exchange_api_key_set=bool(_settings_store.get("exchange_api_key")),
        exchange_api_secret_set=bool(_settings_store.get("exchange_api_secret")),
        telegram_enabled=_settings_store.get("telegram_enabled", False),
        telegram_bot_token_set=bool(_settings_store.get("telegram_bot_token")),
        telegram_chat_id=_settings_store.get("telegram_chat_id", ""),
        openrouter_api_key_set=bool(
            _settings_store.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        ),
        openrouter_model=_settings_store.get("openrouter_model", "anthropic/claude-sonnet-4"),
        timezone=_settings_store.get("timezone", "UTC"),
        language=_settings_store.get("language", "fr"),
        theme=_settings_store.get("theme", "dark"),
    )


# ---------------------------------------------------------------------------
# Read / Update
# ---------------------------------------------------------------------------

@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: dict = Depends(get_current_active_user),
):
    """Get all platform settings (sensitive fields masked)."""
    return _build_response()


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update platform settings."""
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if value is not None:
            _settings_store[key] = value

    return _build_response()


# ---------------------------------------------------------------------------
# Test connections
# ---------------------------------------------------------------------------

@router.post("/test-exchange", response_model=SuccessResponse)
async def test_exchange(
    body: TestExchangeRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Test exchange API connectivity with provided credentials."""
    if body.exchange == "binance":
        try:
            import hashlib
            import hmac
            import time
            import urllib.parse

            timestamp = int(time.time() * 1000)
            query = f"timestamp={timestamp}"
            signature = hmac.new(
                body.api_secret.encode(),
                query.encode(),
                hashlib.sha256,
            ).hexdigest()

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api.binance.com/api/v3/account?{query}&signature={signature}",
                    headers={"X-MBX-APIKEY": body.api_key},
                )
                if resp.status_code == 200:
                    return SuccessResponse(message="Exchange connection successful")
                else:
                    error = resp.json().get("msg", "Unknown error")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Exchange API error: {error}",
                    )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach exchange: {exc}",
            )

    return SuccessResponse(message=f"Exchange {body.exchange} test not yet supported")


@router.post("/test-telegram", response_model=SuccessResponse)
async def test_telegram(
    body: TestTelegramRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Send a test message to Telegram to verify bot token and chat ID."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{body.bot_token}/sendMessage",
                json={
                    "chat_id": body.chat_id,
                    "text": "Kairos Trading - Test message OK",
                },
            )
            if resp.status_code == 200:
                return SuccessResponse(message="Telegram test message sent successfully")
            else:
                error = resp.json().get("description", "Unknown error")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Telegram API error: {error}",
                )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot reach Telegram: {exc}",
        )


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
    from datetime import datetime, timezone

    safe_config = {
        k: v for k, v in _settings_store.items()
        if "key" not in k.lower() and "secret" not in k.lower() and "token" not in k.lower()
    }

    return {
        "config": safe_config,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/restore", response_model=SuccessResponse)
async def restore_config(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Import configuration from a previously exported JSON file."""
    try:
        content = await file.read()
        data = json.loads(content)
        config = data.get("config", {})

        # Merge into settings store (skip sensitive fields)
        for key, value in config.items():
            if "key" not in key.lower() and "secret" not in key.lower() and "token" not in key.lower():
                _settings_store[key] = value

        return SuccessResponse(message=f"Configuration restored ({len(config)} keys)")
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration file: {exc}",
        )
