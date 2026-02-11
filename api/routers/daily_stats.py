"""Daily stats router - daily P&L, history, summary."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth.jwt import get_current_active_user

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class DailyStatResponse(BaseModel):
    """Statistics for a single day."""

    date: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    pnl_usdt: float = 0.0
    pnl_pct: float = 0.0
    volume_usdt: float = 0.0
    fees_usdt: float = 0.0
    max_drawdown_pct: float = 0.0


class DailySummaryResponse(BaseModel):
    """Aggregated summary over a date range."""

    period_start: str
    period_end: str
    total_days: int = 0
    trading_days: int = 0
    total_trades: int = 0
    total_pnl_usdt: float = 0.0
    total_pnl_pct: float = 0.0
    average_daily_pnl: float = 0.0
    best_day_pnl: float = 0.0
    worst_day_pnl: float = 0.0
    win_rate: float = 0.0
    total_fees_usdt: float = 0.0


# ---------------------------------------------------------------------------
# Today
# ---------------------------------------------------------------------------

@router.get("/today", response_model=DailyStatResponse)
async def today_stats(
    current_user: dict = Depends(get_current_active_user),
):
    """Get trading statistics for today."""
    # TODO: query from DB (trades where date = today)
    return DailyStatResponse(date=date.today().isoformat())


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[DailyStatResponse])
async def stats_history(
    start_date: date | None = Query(None, description="Start date (inclusive)"),
    end_date: date | None = Query(None, description="End date (inclusive)"),
    limit: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_active_user),
):
    """Get daily statistics over a date range."""
    # TODO: query from DB, default last 30 days
    return []


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DailySummaryResponse)
async def stats_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """Get aggregated summary over a date range."""
    today = date.today().isoformat()
    # TODO: aggregate from DB
    return DailySummaryResponse(period_start=today, period_end=today)
