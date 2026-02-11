"""Trade-related schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class TradeRecordRequest(BaseModel):
    """Internal request from the trading engine to record a completed trade."""

    pair: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl_usdt: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    strategy_name: str = ""
    entry_reason: str = ""
    exit_reason: str = ""
    metadata: dict | None = None


class TradeJournalRequest(BaseModel):
    """Body for POST /trades/{trade_id}/journal."""

    notes: str = Field(..., max_length=5000)
    tags: list[str] = Field(default_factory=list)
    rating: int | None = Field(None, ge=1, le=5)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class TradeResponse(BaseModel):
    """Single trade representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    pair: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl_usdt: float
    pnl_pct: float
    fees: float
    strategy_name: str
    entry_reason: str
    exit_reason: str
    metadata: dict | None = None
    created_at: datetime


class TradeListResponse(BaseModel):
    """Paginated list of trades."""

    total: int
    page: int
    per_page: int
    pages: int
    trades: list[TradeResponse]


class TradeStatsResponse(BaseModel):
    """Aggregated trade statistics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl_usdt: float = 0.0
    total_pnl_pct: float = 0.0
    average_pnl_usdt: float = 0.0
    max_win_usdt: float = 0.0
    max_loss_usdt: float = 0.0
    average_duration_minutes: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float | None = None


class TradeJournalResponse(BaseModel):
    """Journal entry for a trade."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: int
    notes: str
    tags: list[str]
    rating: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
