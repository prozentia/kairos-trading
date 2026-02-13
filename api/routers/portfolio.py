"""Portfolio router - positions, summary, allocation, risk metrics."""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user
from api.deps import get_db
from api.services.bot_manager import BotManager
from adapters.database.models import Trade

router = APIRouter()
_bot_manager = BotManager()


# ---------------------------------------------------------------------------
# Portfolio Overview (main endpoint for dashboard)
# ---------------------------------------------------------------------------

@router.get("")
async def get_portfolio_overview(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return portfolio overview for the dashboard.

    Combines live engine data (balance, P&L) with DB positions.
    Returns PortfolioOverview shape expected by the frontend.
    """
    # Get live data from engine
    engine_status = await _bot_manager.get_status()
    balance = engine_status.get("balance", 0.0)
    daily_pnl_usdt = engine_status.get("daily_pnl_usdt", 0.0)
    daily_pnl_pct = engine_status.get("daily_pnl_pct", 0.0)
    engine_positions = engine_status.get("positions", [])

    # Compute exposure from engine positions
    in_positions_usdt = sum(
        p.get("entry_price", 0) * p.get("quantity", 0)
        for p in engine_positions
    )

    total_value = balance + in_positions_usdt
    exposure_pct = (in_positions_usdt / total_value * 100) if total_value > 0 else 0.0

    return {
        "total_value_usdt": round(total_value, 2),
        "available_usdt": round(balance, 2),
        "in_positions_usdt": round(in_positions_usdt, 2),
        "exposure_pct": round(exposure_pct, 2),
        "daily_pnl_usdt": round(daily_pnl_usdt, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 2),
        "positions": engine_positions,
    }


# ---------------------------------------------------------------------------
# Positions (DB-backed, for history)
# ---------------------------------------------------------------------------

@router.get("/positions")
async def get_positions(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all open positions from DB."""
    result = await db.execute(
        select(Trade).where(Trade.status == "OPEN").order_by(Trade.entry_time.desc())
    )
    positions = result.scalars().all()

    return [
        {
            "id": p.id,
            "pair": p.pair,
            "side": p.side,
            "entry_price": p.entry_price,
            "quantity": p.quantity,
            "entry_time": p.entry_time.isoformat() if p.entry_time else None,
            "strategy_name": p.strategy_name,
            "entry_reason": p.entry_reason,
            "status": p.status,
        }
        for p in positions
    ]


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def portfolio_summary(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level summary.

    Returns: {total_value_usdt, total_exposure_usdt, exposure_pct,
    total_unrealised_pnl, total_realised_pnl, open_positions_count}.
    """
    # Count open positions
    open_count_result = await db.execute(
        select(func.count(Trade.id)).where(Trade.status == "OPEN")
    )
    open_count = open_count_result.scalar() or 0

    # Sum of open position values (entry_price * quantity)
    exposure_result = await db.execute(
        select(func.sum(Trade.entry_price * Trade.quantity)).where(Trade.status == "OPEN")
    )
    total_exposure = exposure_result.scalar() or 0.0

    # Total realised PnL from closed trades
    realised_result = await db.execute(
        select(func.sum(Trade.pnl_usdt)).where(Trade.status == "CLOSED")
    )
    total_realised = realised_result.scalar() or 0.0

    return {
        "total_value_usdt": round(total_exposure + total_realised, 4),
        "total_exposure_usdt": round(total_exposure, 4),
        "exposure_pct": 0.0,  # Requires knowing total capital
        "total_unrealised_pnl": 0.0,  # Requires live prices
        "total_realised_pnl": round(total_realised, 4),
        "open_positions_count": open_count,
    }


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

@router.get("/allocation")
async def portfolio_allocation(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get allocation breakdown for pie chart visualisation.

    Returns a list of {pair, value_usdt, percentage}.
    """
    result = await db.execute(
        select(
            Trade.pair,
            func.sum(Trade.entry_price * Trade.quantity).label("value_usdt"),
        )
        .where(Trade.status == "OPEN")
        .group_by(Trade.pair)
    )
    rows = result.all()

    total = sum(r.value_usdt for r in rows) if rows else 0.0

    return [
        {
            "pair": r.pair,
            "value_usdt": round(r.value_usdt, 4),
            "percentage": round((r.value_usdt / total * 100), 2) if total > 0 else 0.0,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Risk metrics
# ---------------------------------------------------------------------------

@router.get("/risk-metrics")
async def risk_metrics(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio risk metrics.

    Returns: {max_drawdown_pct, current_drawdown_pct, daily_var,
    sharpe_ratio, sortino_ratio, exposure_pct, daily_loss_pct}.
    """
    # Fetch all closed trades for computing metrics
    result = await db.execute(
        select(Trade)
        .where(Trade.status == "CLOSED")
        .order_by(Trade.exit_time.asc())
    )
    trades = result.scalars().all()

    if not trades:
        return {
            "max_drawdown_pct": 0.0,
            "current_drawdown_pct": 0.0,
            "daily_var": 0.0,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "exposure_pct": 0.0,
            "daily_loss_pct": 0.0,
        }

    # Compute equity curve for drawdown
    pnls = [t.pnl_pct for t in trades]
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    current_dd = peak - cumulative

    # Simple Sharpe ratio approximation (annualized)
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls) if len(pnls) > 1 else 0.0
    std_dev = math.sqrt(variance) if variance > 0 else 0.0
    sharpe = (avg_pnl / std_dev * math.sqrt(252)) if std_dev > 0 else None

    # Sortino ratio (only downside deviation)
    negative_pnls = [p for p in pnls if p < 0]
    if negative_pnls:
        downside_var = sum(p ** 2 for p in negative_pnls) / len(negative_pnls)
        downside_dev = math.sqrt(downside_var)
        sortino = (avg_pnl / downside_dev * math.sqrt(252)) if downside_dev > 0 else None
    else:
        sortino = None

    # Today's loss
    today = datetime.now(timezone.utc).date()
    today_pnl = sum(
        t.pnl_pct for t in trades
        if t.exit_time and t.exit_time.date() == today
    )

    return {
        "max_drawdown_pct": round(max_dd, 4),
        "current_drawdown_pct": round(current_dd, 4),
        "daily_var": round(std_dev * 1.65, 4),  # 95% VaR approximation
        "sharpe_ratio": round(sharpe, 4) if sharpe is not None else None,
        "sortino_ratio": round(sortino, 4) if sortino is not None else None,
        "exposure_pct": 0.0,
        "daily_loss_pct": round(today_pnl, 4),
    }


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

@router.get("/correlation-matrix")
async def correlation_matrix(
    current_user: dict = Depends(get_current_active_user),
):
    """Get pair-to-pair correlation matrix.

    Returns: {pairs: ["BTCUSDT", ...], matrix: [[1.0, 0.8, ...], ...]}.
    Note: Full implementation requires historical price data.
    """
    return {"pairs": [], "matrix": []}
