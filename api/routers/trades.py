"""Trades router - CRUD, stats, export, journal."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse
from api.schemas.trades import (
    TradeJournalRequest,
    TradeJournalResponse,
    TradeListResponse,
    TradeRecordRequest,
    TradeResponse,
    TradeStatsResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# List / Read
# ---------------------------------------------------------------------------

@router.get("/", response_model=TradeListResponse)
async def list_trades(
    pair: str | None = Query(None, description="Filter by trading pair"),
    strategy: str | None = Query(None, description="Filter by strategy name"),
    status_filter: str | None = Query(None, alias="status", description="open / closed"),
    start_date: datetime | None = Query(None, description="Start of date range"),
    end_date: datetime | None = Query(None, description="End of date range"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_active_user),
):
    """List trades with optional filters and pagination."""
    # TODO: query trades from DB with filters
    return TradeListResponse(total=0, page=page, per_page=per_page, pages=0, trades=[])


@router.get("/stats", response_model=TradeStatsResponse)
async def trade_stats(
    pair: str | None = Query(None),
    strategy: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """Return aggregated trade statistics."""
    # TODO: compute stats from DB
    return TradeStatsResponse()


@router.get("/export/csv")
async def export_csv(
    pair: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """Export trades as a CSV file."""
    # TODO: generate CSV from trade data
    async def _generate():
        yield "id,pair,side,entry_price,exit_price,pnl_usdt,pnl_pct\n"
        # TODO: yield rows

    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get a single trade by ID."""
    # TODO: query trade from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Trade {trade_id} not found",
    )


# ---------------------------------------------------------------------------
# Record (internal - from trading engine)
# ---------------------------------------------------------------------------

@router.post(
    "/record-complete",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_trade(body: TradeRecordRequest):
    """Record a completed trade (called by the trading engine).

    Uses internal auth token rather than user JWT.
    """
    # TODO: validate internal token from header
    # TODO: insert trade into DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Trade recording not yet wired to the database",
    )


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

@router.post("/{trade_id}/journal", response_model=TradeJournalResponse, status_code=status.HTTP_201_CREATED)
async def add_journal(
    trade_id: int,
    body: TradeJournalRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Add journal notes to a trade."""
    # TODO: insert journal entry into DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Trade journal not yet wired to the database",
    )


@router.get("/{trade_id}/journal", response_model=list[TradeJournalResponse])
async def get_journal(
    trade_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get all journal entries for a trade."""
    # TODO: query journal from DB
    return []
