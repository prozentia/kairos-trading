"""Tests for core data models (Candle, Signal, Position, Trade, etc.)."""

from datetime import datetime, timezone

import pytest

from core.models import (
    Candle,
    Position,
    PositionStatus,
    RiskLimits,
    Signal,
    SignalType,
    StrategyConfig,
    Trade,
)


# ---------------------------------------------------------------------------
# Candle
# ---------------------------------------------------------------------------

def test_candle_creation(sample_candle):
    """Candle should store all OHLCV fields correctly."""
    c = sample_candle
    assert c.pair == "BTC/USDT"
    assert c.timeframe == "1m"
    assert c.open == 97_500.00
    assert c.high >= max(c.open, c.close)
    assert c.low <= min(c.open, c.close)
    assert c.volume > 0
    assert c.is_closed is True


def test_candle_to_dict_roundtrip(sample_candle):
    """Candle.to_dict() -> Candle.from_dict() should be lossless."""
    d = sample_candle.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["timestamp"], str)

    restored = Candle.from_dict(d)
    assert restored.open == sample_candle.open
    assert restored.high == sample_candle.high
    assert restored.low == sample_candle.low
    assert restored.close == sample_candle.close
    assert restored.volume == sample_candle.volume
    assert restored.pair == sample_candle.pair
    assert restored.timeframe == sample_candle.timeframe
    assert restored.is_closed == sample_candle.is_closed
    # Timestamp should survive the round-trip
    assert restored.timestamp == sample_candle.timestamp


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

def test_signal_creation():
    """Signal should be created with correct fields."""
    sig = Signal(
        type=SignalType.BUY,
        pair="BTC/USDT",
        timeframe="1m",
        price=97_500.0,
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        strategy_name="MSB Glissant",
        reason="BB touch + HA green + MSB break",
        confidence=0.85,
    )
    assert sig.type == SignalType.BUY
    assert sig.is_actionable is True
    assert sig.confidence == 0.85


def test_signal_types():
    """All signal types should be distinguishable and NO_SIGNAL not actionable."""
    now = datetime.now(timezone.utc)

    buy = Signal(type=SignalType.BUY, pair="BTC/USDT", timeframe="1m", price=100, timestamp=now)
    sell = Signal(type=SignalType.SELL, pair="BTC/USDT", timeframe="1m", price=100, timestamp=now)
    emergency = Signal(type=SignalType.EMERGENCY_SELL, pair="BTC/USDT", timeframe="1m", price=100, timestamp=now)
    no_sig = Signal(type=SignalType.NO_SIGNAL, pair="BTC/USDT", timeframe="1m", price=100, timestamp=now)

    assert buy.is_actionable is True
    assert sell.is_actionable is True
    assert emergency.is_actionable is True
    assert no_sig.is_actionable is False

    # Enum values
    assert SignalType.BUY.value == "BUY"
    assert SignalType.SELL.value == "SELL"
    assert SignalType.EMERGENCY_SELL.value == "EMERGENCY_SELL"
    assert SignalType.NO_SIGNAL.value == "NO_SIGNAL"


def test_signal_serialization():
    """Signal to_dict/from_dict round-trip should be lossless."""
    now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
    sig = Signal(
        type=SignalType.BUY,
        pair="BTC/USDT",
        timeframe="5m",
        price=97_000.0,
        timestamp=now,
        strategy_name="test",
        reason="unit test",
        confidence=0.9,
        metadata={"rsi": 28.5},
    )

    d = sig.to_dict()
    assert d["type"] == "BUY"
    assert isinstance(d["timestamp"], str)

    restored = Signal.from_dict(d)
    assert restored.type == SignalType.BUY
    assert restored.pair == sig.pair
    assert restored.metadata == {"rsi": 28.5}


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

def test_position_creation(sample_position):
    """Position should be open with correct entry data."""
    pos = sample_position
    assert pos.is_open is True
    assert pos.status == PositionStatus.OPEN
    assert pos.pair == "BTC/USDT"
    assert pos.entry_price == 97_500.00
    assert pos.quantity == 0.001
    assert pos.stop_loss == 96_037.50


def test_position_status_transitions(sample_position):
    """Position should transition from OPEN to CLOSED."""
    pos = sample_position
    assert pos.is_open is True

    # Close the position
    pos.status = PositionStatus.CLOSED
    pos.exit_price = 98_000.0
    pos.exit_time = datetime(2026, 2, 10, 13, 0, 0, tzinfo=timezone.utc)
    pos.exit_reason = "TRAILING_STOP"

    assert pos.is_open is False
    assert pos.status == PositionStatus.CLOSED
    assert pos.exit_price == 98_000.0

    # Also test CANCELLED status
    pos2 = Position(
        pair="ETH/USDT",
        side="BUY",
        entry_price=3200.0,
        quantity=0.1,
        entry_time=datetime.now(timezone.utc),
    )
    pos2.status = PositionStatus.CANCELLED
    assert pos2.is_open is False
    assert pos2.status == PositionStatus.CANCELLED


def test_position_update_pnl(sample_position):
    """update_pnl should correctly calculate unrealised PnL percentage."""
    pos = sample_position

    # Price goes up 1%
    pos.update_pnl(98_475.0)
    assert pos.current_pnl_pct == pytest.approx(1.0, rel=0.01)

    # Price goes down 1.5% (at stop-loss)
    pos.update_pnl(96_037.50)
    assert pos.current_pnl_pct == pytest.approx(-1.5, rel=0.01)


def test_position_notional_value(sample_position):
    """notional_value should return entry_price * quantity."""
    pos = sample_position
    expected = 97_500.0 * 0.001
    assert pos.notional_value == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

def test_trade_creation(sample_trade):
    """Trade should store complete round-trip data."""
    t = sample_trade
    assert t.pair == "BTC/USDT"
    assert t.entry_price == 97_500.0
    assert t.exit_price == 98_100.0
    assert t.pnl_usdt == 0.60
    assert t.strategy_name == "MSB Glissant"
    assert t.entry_reason == "MSB_BREAK"
    assert t.exit_reason == "TRAILING_STOP"
    assert t.id  # UUID should be set


def test_trade_from_position(sample_position):
    """Trade.from_position should correctly create a trade from a closed position."""
    pos = sample_position
    pos.status = PositionStatus.CLOSED
    pos.exit_price = 98_000.0
    pos.exit_time = datetime(2026, 2, 10, 13, 0, 0, tzinfo=timezone.utc)
    pos.exit_reason = "TAKE_PROFIT"
    pos.update_pnl(pos.exit_price)

    trade = Trade.from_position(pos, fees=0.05)
    assert trade.pair == "BTC/USDT"
    assert trade.entry_price == 97_500.0
    assert trade.exit_price == 98_000.0
    assert trade.exit_reason == "TAKE_PROFIT"
    assert trade.entry_reason == "MSB_BREAK"
    assert trade.fees == 0.05
    # PnL = (98000 - 97500) * 0.001 - 0.05 = 0.5 - 0.05 = 0.45
    assert trade.pnl_usdt == pytest.approx(0.45)


def test_trade_serialization(sample_trade):
    """Trade to_dict/from_dict round-trip should be lossless."""
    d = sample_trade.to_dict()
    restored = Trade.from_dict(d)
    assert restored.pair == sample_trade.pair
    assert restored.pnl_usdt == sample_trade.pnl_usdt
    assert restored.entry_reason == sample_trade.entry_reason


# ---------------------------------------------------------------------------
# RiskLimits & StrategyConfig
# ---------------------------------------------------------------------------

def test_risk_limits_defaults():
    """RiskLimits should have sensible defaults."""
    r = RiskLimits()
    assert r.max_positions == 3
    assert r.max_daily_loss_pct == 5.0
    assert r.max_drawdown_pct == 15.0


def test_risk_limits_serialization(sample_risk_limits):
    """RiskLimits to_dict/from_dict round-trip."""
    d = sample_risk_limits.to_dict()
    restored = RiskLimits.from_dict(d)
    assert restored.max_positions == sample_risk_limits.max_positions
    assert restored.max_daily_loss_pct == sample_risk_limits.max_daily_loss_pct


def test_strategy_config_creation(sample_strategy_config):
    """StrategyConfig should store all strategy fields."""
    cfg = sample_strategy_config
    assert cfg.name == "MSB Glissant"
    assert cfg.is_active is True
    assert "BTC/USDT" in cfg.pairs
    assert "heikin_ashi" in cfg.indicators_needed
    assert cfg.entry_conditions["logic"] == "AND"
    assert len(cfg.entry_conditions["conditions"]) == 3


def test_strategy_config_serialization(sample_strategy_config):
    """StrategyConfig to_dict/from_dict round-trip."""
    d = sample_strategy_config.to_dict()
    restored = StrategyConfig.from_dict(d)
    assert restored.name == sample_strategy_config.name
    assert restored.pairs == sample_strategy_config.pairs
    assert restored.timeframe == sample_strategy_config.timeframe
