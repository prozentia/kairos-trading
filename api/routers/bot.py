"""Bot control router - start, stop, restart, config, logs."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class BotStatusResponse(BaseModel):
    """Current bot status."""

    running: bool = False
    uptime_seconds: int = 0
    pairs_active: list[str] = []
    open_positions: int = 0
    last_signal_time: str | None = None
    mode: str = "dry_run"
    version: str = "1.0.0"


class BotConfigResponse(BaseModel):
    """Bot configuration snapshot."""

    dry_run: bool = True
    pairs: list[str] = []
    strategy_type: str = ""
    ha_timeframe: str = "5m"
    entry_timeframe: str = "1m"
    stop_loss_pct: float = 1.5
    trailing_activation_pct: float = 0.6
    trailing_distance_pct: float = 0.3
    use_full_balance: bool = True
    trade_capital_usdt: float = 100.0
    telegram_enabled: bool = True


class BotConfigUpdateRequest(BaseModel):
    """Body for PUT /bot/config (partial update)."""

    dry_run: bool | None = None
    pairs: list[str] | None = None
    strategy_type: str | None = None
    ha_timeframe: str | None = None
    entry_timeframe: str | None = None
    stop_loss_pct: float | None = None
    trailing_activation_pct: float | None = None
    trailing_distance_pct: float | None = None
    use_full_balance: bool | None = None
    trade_capital_usdt: float | None = None
    telegram_enabled: bool | None = None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status", response_model=BotStatusResponse)
async def bot_status(
    current_user: dict = Depends(get_current_active_user),
):
    """Get current bot status."""
    # TODO: call bot_manager.get_status()
    return BotStatusResponse()


# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------

@router.post("/start", response_model=SuccessResponse)
async def start_bot(
    current_user: dict = Depends(get_current_active_user),
):
    """Start the trading bot."""
    # TODO: call bot_manager.start()
    return SuccessResponse(message="Bot start command sent")


@router.post("/stop", response_model=SuccessResponse)
async def stop_bot(
    current_user: dict = Depends(get_current_active_user),
):
    """Stop the trading bot gracefully."""
    # TODO: call bot_manager.stop()
    return SuccessResponse(message="Bot stop command sent")


@router.post("/restart", response_model=SuccessResponse)
async def restart_bot(
    current_user: dict = Depends(get_current_active_user),
):
    """Restart the trading bot."""
    # TODO: call bot_manager.restart()
    return SuccessResponse(message="Bot restart command sent")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@router.get("/config", response_model=BotConfigResponse)
async def get_config(
    current_user: dict = Depends(get_current_active_user),
):
    """Get current bot configuration."""
    # TODO: read from config file / DB
    return BotConfigResponse()


@router.put("/config", response_model=BotConfigResponse)
async def update_config(
    body: BotConfigUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update bot configuration.

    Note: some changes require a bot restart to take effect.
    """
    # TODO: validate + write to config file / DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Config update not yet wired",
    )


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@router.get("/logs")
async def get_logs(
    lines: int = Query(100, ge=1, le=1000, description="Number of lines to return"),
    level: str | None = Query(None, description="Filter by log level (INFO, WARNING, ERROR)"),
    current_user: dict = Depends(get_current_active_user),
):
    """Get last N lines of bot logs.

    Returns: {"lines": ["2026-02-11 10:00:00 [INFO] ...", ...]}.
    """
    # TODO: call bot_manager.get_logs(lines, level)
    return {"lines": []}
