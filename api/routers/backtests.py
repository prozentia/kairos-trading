"""Backtests router - launch, status, results, compare."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user
from api.deps import get_db
from api.schemas.common import SuccessResponse
from adapters.database.models import Backtest, Strategy

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class BacktestLaunchRequest(BaseModel):
    """Body for POST /backtests/."""

    strategy_id: str
    pair: str = "BTCUSDT"
    timeframe: str = "5m"
    start_date: str = Field(..., description="ISO date string")
    end_date: str = Field(..., description="ISO date string")
    initial_capital: float = 1000.0
    fees_pct: float = 0.1


class BacktestCompareRequest(BaseModel):
    """Body for POST /backtests/compare."""

    backtest_ids: list[str] = Field(..., min_length=2)


class BacktestStatusResponse(BaseModel):
    """Progress of a running backtest."""

    id: str
    status: str = "pending"  # pending, running, completed, failed
    progress_pct: float = 0.0
    message: str = ""


class BacktestResultResponse(BaseModel):
    """Full backtest result."""

    id: str
    strategy_id: str
    pair: str
    start_date: str
    end_date: str
    results_json: str = "{}"
    created_at: str = ""


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

@router.post("/", response_model=BacktestStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def launch_backtest(
    body: BacktestLaunchRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Launch a new backtest (async task).

    Returns immediately with a backtest ID and status=pending.
    Use GET /backtests/{id}/status to poll progress.
    """
    # Validate strategy exists
    result = await db.execute(
        select(Strategy).where(Strategy.id == body.strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {body.strategy_id} not found",
        )

    # Create backtest record with pending status
    results = json.dumps({
        "status": "pending",
        "progress_pct": 0.0,
        "initial_capital": body.initial_capital,
        "fees_pct": body.fees_pct,
        "timeframe": body.timeframe,
    })

    backtest = Backtest(
        strategy_id=body.strategy_id,
        pair=body.pair.upper(),
        start_date=datetime.fromisoformat(body.start_date),
        end_date=datetime.fromisoformat(body.end_date),
        results_json=results,
    )
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)

    # TODO: enqueue the actual backtest computation to a background task / Celery

    return BacktestStatusResponse(
        id=backtest.id,
        status="pending",
        progress_pct=0.0,
        message="Backtest queued for execution",
    )


# ---------------------------------------------------------------------------
# Status / Result
# ---------------------------------------------------------------------------

@router.get("/{backtest_id}/status", response_model=BacktestStatusResponse)
async def backtest_status(
    backtest_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get progress of a running backtest."""
    result = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id)
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {backtest_id} not found",
        )

    # Parse status from results_json
    try:
        results = json.loads(backtest.results_json)
    except (json.JSONDecodeError, TypeError):
        results = {}

    return BacktestStatusResponse(
        id=backtest.id,
        status=results.get("status", "pending"),
        progress_pct=results.get("progress_pct", 0.0),
        message=results.get("message", ""),
    )


@router.get("/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest(
    backtest_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full result of a completed backtest."""
    result = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id)
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {backtest_id} not found",
        )

    return BacktestResultResponse(
        id=backtest.id,
        strategy_id=backtest.strategy_id,
        pair=backtest.pair,
        start_date=backtest.start_date.isoformat(),
        end_date=backtest.end_date.isoformat(),
        results_json=backtest.results_json,
        created_at=backtest.created_at.isoformat() if backtest.created_at else "",
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[BacktestResultResponse])
async def list_backtests(
    strategy_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List backtest history."""
    q = select(Backtest).order_by(Backtest.created_at.desc()).limit(limit)
    if strategy_id:
        q = q.where(Backtest.strategy_id == strategy_id)

    result = await db.execute(q)
    backtests = result.scalars().all()

    return [
        BacktestResultResponse(
            id=bt.id,
            strategy_id=bt.strategy_id,
            pair=bt.pair,
            start_date=bt.start_date.isoformat(),
            end_date=bt.end_date.isoformat(),
            results_json=bt.results_json,
            created_at=bt.created_at.isoformat() if bt.created_at else "",
        )
        for bt in backtests
    ]


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

@router.post("/compare")
async def compare_backtests(
    body: BacktestCompareRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare two or more backtest results side by side.

    Returns a comparison table with key metrics for each backtest.
    """
    results = []
    for bt_id in body.backtest_ids:
        result = await db.execute(select(Backtest).where(Backtest.id == bt_id))
        backtest = result.scalar_one_or_none()
        if backtest:
            try:
                parsed = json.loads(backtest.results_json)
            except (json.JSONDecodeError, TypeError):
                parsed = {}

            results.append({
                "id": backtest.id,
                "strategy_id": backtest.strategy_id,
                "pair": backtest.pair,
                "start_date": backtest.start_date.isoformat(),
                "end_date": backtest.end_date.isoformat(),
                "results": parsed,
            })

    return {"backtests": results, "comparison": {}}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{backtest_id}", response_model=SuccessResponse)
async def delete_backtest(
    backtest_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a backtest and its results."""
    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {backtest_id} not found",
        )

    await db.delete(backtest)
    await db.commit()
    return SuccessResponse(message=f"Backtest {backtest_id} deleted")
