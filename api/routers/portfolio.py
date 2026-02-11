"""Portfolio router - positions, summary, allocation, risk metrics."""

from fastapi import APIRouter, Depends

from api.auth.jwt import get_current_active_user

router = APIRouter()


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

@router.get("/")
async def get_positions(
    current_user: dict = Depends(get_current_active_user),
):
    """Get all current open positions.

    Returns a list of {pair, side, entry_price, quantity, current_price,
    unrealised_pnl, unrealised_pnl_pct, stop_loss, trailing_active}.
    """
    # TODO: query open positions from DB / engine state
    return []


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def portfolio_summary(
    current_user: dict = Depends(get_current_active_user),
):
    """Get portfolio-level summary.

    Returns: {total_value_usdt, total_exposure_usdt, exposure_pct,
    total_unrealised_pnl, total_realised_pnl, open_positions_count}.
    """
    # TODO: aggregate from DB / exchange
    return {
        "total_value_usdt": 0.0,
        "total_exposure_usdt": 0.0,
        "exposure_pct": 0.0,
        "total_unrealised_pnl": 0.0,
        "total_realised_pnl": 0.0,
        "open_positions_count": 0,
    }


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

@router.get("/allocation")
async def portfolio_allocation(
    current_user: dict = Depends(get_current_active_user),
):
    """Get allocation breakdown for pie chart visualisation.

    Returns a list of {pair, value_usdt, percentage}.
    """
    # TODO: compute from open positions
    return []


# ---------------------------------------------------------------------------
# Risk metrics
# ---------------------------------------------------------------------------

@router.get("/risk-metrics")
async def risk_metrics(
    current_user: dict = Depends(get_current_active_user),
):
    """Get portfolio risk metrics.

    Returns: {max_drawdown_pct, current_drawdown_pct, daily_var,
    sharpe_ratio, sortino_ratio, exposure_pct, daily_loss_pct}.
    """
    # TODO: compute from trade history + positions
    return {
        "max_drawdown_pct": 0.0,
        "current_drawdown_pct": 0.0,
        "daily_var": 0.0,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "exposure_pct": 0.0,
        "daily_loss_pct": 0.0,
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
    """
    # TODO: compute correlation from historical returns
    return {"pairs": [], "matrix": []}
