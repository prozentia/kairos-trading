"""Core data models for the Kairos Trading platform.

All models are pure Python dataclasses with no external dependencies.
They represent the fundamental domain objects: candles, signals,
positions, trades, risk limits, and strategy configuration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any


class BotState(Enum):
    """Bot operational state."""
    ACTIVE = "ACTIVE"
    SAFE_MODE = "SAFE_MODE"
    HALTED = "HALTED"


class SignalType(Enum):
    """Type of trading signal emitted by a strategy."""
    BUY = "BUY"
    SELL = "SELL"
    EMERGENCY_SELL = "EMERGENCY_SELL"
    NO_SIGNAL = "NO_SIGNAL"


class PositionStatus(Enum):
    """Lifecycle status of a position."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass
class Candle:
    """A single OHLCV candlestick."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    pair: str
    timeframe: str
    is_closed: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Candle:
        d = dict(data)
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


@dataclass
class HeikinAshi:
    """A Heikin-Ashi transformed candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    is_green: bool
    pair: str
    timeframe: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HeikinAshi:
        d = dict(data)
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


@dataclass
class Signal:
    """A trading signal produced by strategy evaluation."""

    type: SignalType
    pair: str
    timeframe: str
    price: float
    timestamp: datetime
    strategy_name: str = ""
    reason: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        """Return True if the signal requires an order action."""
        return self.type in (SignalType.BUY, SignalType.SELL, SignalType.EMERGENCY_SELL)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        d = dict(data)
        d["type"] = SignalType(d["type"])
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


@dataclass
class Position:
    """An open or closed trading position."""

    pair: str
    side: str  # "BUY" or "SELL"
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float = 0.0
    trailing_active: bool = False
    trailing_high: float = 0.0
    take_profit_levels: list[dict[str, float]] = field(default_factory=list)
    current_pnl_pct: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    exit_price: float | None = None
    exit_time: datetime | None = None
    exit_reason: str = ""
    entry_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        return self.status == PositionStatus.OPEN

    @property
    def notional_value(self) -> float:
        """Position value at entry in quote currency."""
        return self.entry_price * self.quantity

    def update_pnl(self, current_price: float) -> None:
        """Recalculate unrealised PnL percentage."""
        if self.entry_price > 0:
            self.current_pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["entry_time"] = self.entry_time.isoformat()
        if self.exit_time:
            data["exit_time"] = self.exit_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Position:
        d = dict(data)
        d["status"] = PositionStatus(d["status"])
        if isinstance(d.get("entry_time"), str):
            d["entry_time"] = datetime.fromisoformat(d["entry_time"])
        if isinstance(d.get("exit_time"), str):
            d["exit_time"] = datetime.fromisoformat(d["exit_time"])
        return cls(**d)


@dataclass
class Trade:
    """A completed trade (entry + exit) for record-keeping."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pair: str = ""
    side: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    entry_time: datetime | None = None
    exit_time: datetime | None = None
    pnl_usdt: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    strategy_name: str = ""
    entry_reason: str = ""
    exit_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_position(cls, position: Position, fees: float = 0.0) -> Trade:
        """Create a Trade record from a closed Position."""
        exit_price = position.exit_price or 0.0
        pnl_usdt = (exit_price - position.entry_price) * position.quantity - fees
        pnl_pct = position.current_pnl_pct
        return cls(
            pair=position.pair,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            entry_time=position.entry_time,
            exit_time=position.exit_time,
            pnl_usdt=pnl_usdt,
            pnl_pct=pnl_pct,
            fees=fees,
            entry_reason=position.entry_reason,
            exit_reason=position.exit_reason,
            metadata=dict(position.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.entry_time:
            data["entry_time"] = self.entry_time.isoformat()
        if self.exit_time:
            data["exit_time"] = self.exit_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trade:
        d = dict(data)
        for k in ("entry_time", "exit_time"):
            if isinstance(d.get(k), str):
                d[k] = datetime.fromisoformat(d[k])
        return cls(**d)


@dataclass
class RiskLimits:
    """Portfolio-level risk parameters."""

    max_positions: int = 3
    max_exposure_pct: float = 50.0
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 15.0
    position_size_pct: float = 10.0
    max_daily_trades: int = 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskLimits:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StrategyConfig:
    """Parsed strategy definition loaded from JSON."""

    name: str = ""
    version: str = "1.0"
    description: str = ""
    pairs: list[str] = field(default_factory=list)
    timeframe: str = "5m"
    entry_conditions: Any = field(default_factory=dict)
    exit_conditions: Any = field(default_factory=dict)
    filters: Any = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    indicators_needed: list[str] = field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MarketSnapshot:
    """A point-in-time view of market state for a symbol."""

    timestamp: int
    symbol: str
    last_price: float
    bid: float
    ask: float
    spread_bps: float
    volume_1m: float
    volume_ratio_vs_avg: float
    candles: dict[str, list[Candle]] = field(default_factory=dict)
    open_interest: float = 0.0
    funding_rate: float = 0.0
    macro_risk_score: float = 0.0
    bot_state: BotState = BotState.ACTIVE
    indicator_states: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bot_state"] = self.bot_state.value
        return data


@dataclass
class AgentSignal:
    """Signal produced by an AI analyst agent."""

    agent: str  # "technical" | "momentum" | "context" | "risk"
    timestamp: int
    signal_score: float  # 0.0 – 1.0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TradeProposal:
    """A proposal to open a trade, pending risk gate validation."""

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: int = 0
    symbol: str = ""
    action: str = "NO_TRADE"  # "BUY" | "NO_TRADE"
    confidence: float = 0.0
    entry_price_ref: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    reward_risk_ratio: float = 0.0
    setup_type: str = ""
    reason: list[str] = field(default_factory=list)
    agent_scores: dict[str, float] = field(default_factory=dict)
    status: str = "PENDING_RISK_GATE"  # "PENDING_RISK_GATE" | "APPROVED" | "REJECTED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskGateResult:
    """Result of a risk gate evaluation on a trade proposal."""

    proposal_id: str = ""
    gate_decision: str = "APPROVED"  # "APPROVED" | "REJECTED"
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskConfig:
    """Risk management parameters for the risk gate."""

    max_spread_bps: float = 2.0
    max_slippage_bps: float = 3.0
    min_confidence: float = 0.60
    min_reward_risk: float = 2.0
    max_daily_loss_pct: float = 2.0
    max_trades_per_day: int = 10
    max_concurrent_positions: int = 1
    max_exposure_pct: float = 1.0
    max_atr_zscore: float = 3.0
    max_macro_risk_score: float = 0.70
    risk_per_trade_pct: float = 0.82

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionState:
    """Tracks the current trading session state."""

    date: str = ""
    trades_today: int = 0
    pnl_today_pct: float = 0.0
    open_positions: int = 0
    open_positions_by_pair: dict[str, int] = field(default_factory=dict)
    exposure_by_pair: dict[str, float] = field(default_factory=dict)
    total_exposure_pct: float = 0.0
    max_drawdown_today_pct: float = 0.0
    circuit_breaker_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
