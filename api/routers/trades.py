"""Trades router - CRUD, stats, export, journal."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user, verify_internal_token
from api.deps import get_db
from api.schemas.common import SuccessResponse
from api.schemas.trades import (
    TradeJournalRequest,
    TradeJournalResponse,
    TradeListResponse,
    TradeRecordRequest,
    TradeResponse,
    TradeStatsResponse,
)
from api.services.trade_service import TradeService

router = APIRouter()


# ---------------------------------------------------------------------------
# List / Read
# ---------------------------------------------------------------------------

@router.get("", response_model=TradeListResponse)
async def list_trades(
    pair: str | None = Query(None, description="Filter by trading pair"),
    strategy: str | None = Query(None, description="Filter by strategy name"),
    status_filter: str | None = Query(None, alias="status", description="open / closed"),
    start_date: datetime | None = Query(None, description="Start of date range"),
    end_date: datetime | None = Query(None, description="End of date range"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List trades with optional filters and pagination."""
    service = TradeService(db)
    result = await service.list_trades(
        user_id=current_user.get("sub"),
        pair=pair,
        strategy=strategy,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
    )
    return TradeListResponse(
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        pages=result["pages"],
        trades=[TradeResponse.model_validate(t) for t in result["trades"]],
    )


@router.get("/stats", response_model=TradeStatsResponse)
async def trade_stats(
    pair: str | None = Query(None),
    strategy: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated trade statistics."""
    service = TradeService(db)
    stats = await service.compute_stats(
        user_id=current_user.get("sub"),
        pair=pair,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
    )
    return TradeStatsResponse(**stats)


@router.get("/export/csv")
async def export_csv(
    pair: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Export trades as a CSV file."""
    service = TradeService(db)
    csv_content = await service.export_csv(
        user_id=current_user.get("sub"),
        pair=pair,
        start_date=start_date,
        end_date=end_date,
    )

    async def _generate():
        yield csv_content

    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single trade by ID."""
    service = TradeService(db)
    trade = await service.get_trade(trade_id)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade {trade_id} not found",
        )
    return TradeResponse.model_validate(trade)


# ---------------------------------------------------------------------------
# Record (internal - from trading engine)
# ---------------------------------------------------------------------------

@router.post(
    "/record-complete",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_trade(
    body: TradeRecordRequest,
    x_internal_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Record a completed trade (called by the trading engine).

    Uses internal auth token rather than user JWT.
    """
    if not x_internal_token or not verify_internal_token(x_internal_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal token",
        )

    service = TradeService(db)
    trade = await service.record_trade(body.model_dump())
    return TradeResponse.model_validate(trade)


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

@router.post(
    "/{trade_id}/journal",
    response_model=TradeJournalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_journal(
    trade_id: str,
    body: TradeJournalRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add journal notes to a trade."""
    service = TradeService(db)
    try:
        entry = await service.add_journal_entry(
            trade_id=trade_id,
            notes=body.notes,
            tags=body.tags,
            rating=body.rating,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade {trade_id} not found",
        )
    return TradeJournalResponse.model_validate(entry)


@router.get("/{trade_id}/journal", response_model=list[TradeJournalResponse])
async def get_journal(
    trade_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all journal entries for a trade."""
    service = TradeService(db)
    entries = await service.get_journal_entries(trade_id)
    return [TradeJournalResponse.model_validate(e) for e in entries]
