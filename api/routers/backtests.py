"""Backtests router - launch, status, results, compare."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class BacktestLaunchRequest(BaseModel):
    """Body for POST /backtests/."""

    strategy_id: int
    pair: str = "BTCUSDT"
    timeframe: str = "5m"
    start_date: str = Field(..., description="ISO date string")
    end_date: str = Field(..., description="ISO date string")
    initial_capital: float = 1000.0
    fees_pct: float = 0.1


class BacktestCompareRequest(BaseModel):
    """Body for POST /backtests/compare."""

    backtest_ids: list[int] = Field(..., min_length=2)


class BacktestStatusResponse(BaseModel):
    """Progress of a running backtest."""

    id: int
    status: str = "pending"  # pending, running, completed, failed
    progress_pct: float = 0.0
    message: str = ""


class BacktestResultResponse(BaseModel):
    """Full backtest result."""

    id: int
    strategy_id: int
    pair: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl_usdt: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float | None = None
    profit_factor: float = 0.0
    trades: list[dict] = Field(default_factory=list)
    equity_curve: list[dict] = Field(default_factory=list)
    status: str = "completed"
    created_at: str = ""


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

@router.post("/", response_model=BacktestStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def launch_backtest(
    body: BacktestLaunchRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Launch a new backtest (async task).

    Returns immediately with a backtest ID and status=pending.
    Use GET /backtests/{id}/status to poll progress.
    """
    # TODO: validate strategy exists, enqueue backtest task
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Backtest launch not yet implemented",
    )


# ---------------------------------------------------------------------------
# Status / Result
# ---------------------------------------------------------------------------

@router.get("/{backtest_id}/status", response_model=BacktestStatusResponse)
async def backtest_status(
    backtest_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get progress of a running backtest."""
    # TODO: check task queue / DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Backtest {backtest_id} not found",
    )


@router.get("/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest(
    backtest_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get full result of a completed backtest."""
    # TODO: query from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Backtest {backtest_id} not found",
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[BacktestResultResponse])
async def list_backtests(
    strategy_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user),
):
    """List backtest history."""
    # TODO: query from DB
    return []


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

@router.post("/compare")
async def compare_backtests(
    body: BacktestCompareRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Compare two or more backtest results side by side.

    Returns a comparison table with key metrics for each backtest.
    """
    # TODO: load results by IDs and build comparison
    return {"backtests": [], "comparison": {}}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{backtest_id}", response_model=SuccessResponse)
async def delete_backtest(
    backtest_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a backtest and its results."""
    # TODO: delete from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Backtest {backtest_id} not found",
    )
