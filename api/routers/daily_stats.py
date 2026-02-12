"""Daily stats router - daily P&L, history, summary."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user
from api.deps import get_db
from adapters.database.models import DailyStat, Trade

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
    db: AsyncSession = Depends(get_db),
):
    """Get trading statistics for today."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Query today's closed trades
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.status == "CLOSED",
                Trade.exit_time >= today_start,
                Trade.exit_time <= today_end,
            )
        )
    )
    trades = result.scalars().all()

    total = len(trades)
    winning = sum(1 for t in trades if t.pnl_usdt > 0)
    losing = sum(1 for t in trades if t.pnl_usdt < 0)
    total_pnl = sum(t.pnl_usdt for t in trades)
    total_pnl_pct = sum(t.pnl_pct for t in trades)
    total_fees = sum(t.fees for t in trades)
    total_volume = sum(t.entry_price * t.quantity for t in trades)

    return DailyStatResponse(
        date=today.isoformat(),
        total_trades=total,
        winning_trades=winning,
        losing_trades=losing,
        win_rate=round(winning / total * 100, 2) if total else 0.0,
        pnl_usdt=round(total_pnl, 4),
        pnl_pct=round(total_pnl_pct, 4),
        volume_usdt=round(total_volume, 4),
        fees_usdt=round(total_fees, 4),
        max_drawdown_pct=0.0,
    )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[DailyStatResponse])
async def stats_history(
    start_date: date | None = Query(None, description="Start date (inclusive)"),
    end_date: date | None = Query(None, description="End date (inclusive)"),
    limit: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily statistics over a date range."""
    # Check daily_stats table first
    q = select(DailyStat).order_by(DailyStat.date.desc()).limit(limit)
    conditions = []
    if start_date:
        conditions.append(DailyStat.date >= start_date)
    if end_date:
        conditions.append(DailyStat.date <= end_date)
    if conditions:
        q = q.where(and_(*conditions))

    result = await db.execute(q)
    daily_stats = result.scalars().all()

    if daily_stats:
        return [
            DailyStatResponse(
                date=ds.date.isoformat(),
                total_trades=ds.total_trades,
                winning_trades=ds.winning_trades,
                losing_trades=ds.total_trades - ds.winning_trades,
                win_rate=round(ds.winning_trades / ds.total_trades * 100, 2)
                if ds.total_trades > 0 else 0.0,
                pnl_usdt=ds.pnl_usdt,
                max_drawdown_pct=ds.max_drawdown,
            )
            for ds in daily_stats
        ]

    # Fallback: compute from trades table
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=limit)

    # Group trades by exit date
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.status == "CLOSED",
                Trade.exit_time.isnot(None),
            )
        ).order_by(Trade.exit_time.desc())
    )
    trades = result.scalars().all()

    # Group by day
    day_map: dict[str, list] = {}
    for t in trades:
        if t.exit_time:
            day_key = t.exit_time.date().isoformat()
            if day_key not in day_map:
                day_map[day_key] = []
            day_map[day_key].append(t)

    # Filter by date range and build response
    stats = []
    for day_str in sorted(day_map.keys(), reverse=True)[:limit]:
        day = date.fromisoformat(day_str)
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue

        day_trades = day_map[day_str]
        total = len(day_trades)
        winning = sum(1 for t in day_trades if t.pnl_usdt > 0)
        total_pnl = sum(t.pnl_usdt for t in day_trades)
        total_pnl_pct = sum(t.pnl_pct for t in day_trades)
        total_fees = sum(t.fees for t in day_trades)

        stats.append(DailyStatResponse(
            date=day_str,
            total_trades=total,
            winning_trades=winning,
            losing_trades=total - winning,
            win_rate=round(winning / total * 100, 2) if total else 0.0,
            pnl_usdt=round(total_pnl, 4),
            pnl_pct=round(total_pnl_pct, 4),
            fees_usdt=round(total_fees, 4),
        ))

    return stats


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DailySummaryResponse)
async def stats_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated summary over a date range."""
    today = date.today()
    if not end_date:
        end_date = today
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Query closed trades in range
    conditions = [Trade.status == "CLOSED"]
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    conditions.append(Trade.exit_time >= start_dt)
    conditions.append(Trade.exit_time <= end_dt)

    result = await db.execute(
        select(Trade).where(and_(*conditions))
    )
    trades = result.scalars().all()

    total_trades = len(trades)
    total_pnl = sum(t.pnl_usdt for t in trades)
    total_pnl_pct = sum(t.pnl_pct for t in trades)
    total_fees = sum(t.fees for t in trades)
    winning = sum(1 for t in trades if t.pnl_usdt > 0)

    # Group by day for daily analysis
    day_pnls: dict[str, float] = {}
    for t in trades:
        if t.exit_time:
            day_key = t.exit_time.date().isoformat()
            day_pnls[day_key] = day_pnls.get(day_key, 0.0) + t.pnl_usdt

    trading_days = len(day_pnls)
    total_days = (end_date - start_date).days + 1
    avg_daily = total_pnl / trading_days if trading_days else 0.0
    best_day = max(day_pnls.values()) if day_pnls else 0.0
    worst_day = min(day_pnls.values()) if day_pnls else 0.0

    return DailySummaryResponse(
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
        total_days=total_days,
        trading_days=trading_days,
        total_trades=total_trades,
        total_pnl_usdt=round(total_pnl, 4),
        total_pnl_pct=round(total_pnl_pct, 4),
        average_daily_pnl=round(avg_daily, 4),
        best_day_pnl=round(best_day, 4),
        worst_day_pnl=round(worst_day, 4),
        win_rate=round(winning / total_trades * 100, 2) if total_trades else 0.0,
        total_fees_usdt=round(total_fees, 4),
    )
