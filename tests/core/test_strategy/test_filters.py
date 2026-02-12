"""Tests for post-signal filters.

Filters run after a signal is generated to decide whether it should be
forwarded to the engine (e.g. trend confirmation, time restrictions,
cooldown after loss, volume, volatility, spread, consecutive).
"""

from datetime import datetime, timedelta, timezone

import pytest

from core.models import Candle, Signal, SignalType, StrategyConfig
from core.strategy.filters import SignalFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _buy_signal(
    price: float = 97_500.0,
    ts: datetime | None = None,
) -> Signal:
    """Create a BUY signal for testing."""
    return Signal(
        type=SignalType.BUY,
        pair="BTC/USDT",
        timeframe="5m",
        price=price,
        timestamp=ts or datetime(2026, 2, 10, 14, 30, 0, tzinfo=timezone.utc),
        strategy_name="test",
    )


def _sell_signal(price: float = 97_500.0) -> Signal:
    """Create a SELL signal for testing."""
    return Signal(
        type=SignalType.SELL,
        pair="BTC/USDT",
        timeframe="5m",
        price=price,
        timestamp=datetime(2026, 2, 10, 14, 30, 0, tzinfo=timezone.utc),
        strategy_name="test",
    )


def _candle(close: float, volume: float = 5.0, high: float | None = None, low: float | None = None) -> Candle:
    """Create a minimal candle."""
    return Candle(
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        open=close - 50,
        high=high if high is not None else close + 100,
        low=low if low is not None else close - 100,
        close=close,
        volume=volume,
        pair="BTC/USDT",
        timeframe="5m",
    )


def _candles_with_trend(
    count: int = 60,
    start: float = 97_000.0,
    step: float = 10.0,
    volume: float = 5.0,
) -> list[Candle]:
    """Generate candles with an upward trend."""
    candles = []
    for i in range(count):
        price = start + i * step
        candles.append(_candle(close=price, volume=volume))
    return candles


@pytest.fixture
def sf() -> SignalFilter:
    return SignalFilter()


# ---------------------------------------------------------------------------
# Trend filter
# ---------------------------------------------------------------------------

class TestFilterByTrend:
    """Test trend (SMA) filter."""

    def test_buy_above_sma_passes(self, sf: SignalFilter):
        """BUY when price is above SMA should pass."""
        candles = _candles_with_trend(count=60, start=97_000.0, step=10.0)
        # SMA50 of last 50 candles, all below latest
        signal = _buy_signal(price=candles[-1].close + 100)
        result = sf.filter_by_trend(signal, candles, period=50)
        assert result.type == SignalType.BUY

    def test_buy_below_sma_blocked(self, sf: SignalFilter):
        """BUY when price is below SMA should be blocked."""
        candles = _candles_with_trend(count=60, start=97_000.0, step=10.0)
        sma = sum(c.close for c in candles[-50:]) / 50
        signal = _buy_signal(price=sma - 500)
        result = sf.filter_by_trend(signal, candles, period=50)
        assert result.type == SignalType.NO_SIGNAL

    def test_not_enough_candles_passes(self, sf: SignalFilter):
        """When not enough candles, let the signal through."""
        candles = [_candle(close=97_500.0)] * 10
        signal = _buy_signal(price=90_000.0)
        result = sf.filter_by_trend(signal, candles, period=50)
        assert result.type == SignalType.BUY

    def test_no_signal_passthrough(self, sf: SignalFilter):
        """NO_SIGNAL should pass through unchanged."""
        no_sig = Signal(
            type=SignalType.NO_SIGNAL,
            pair="BTC/USDT", timeframe="5m", price=97_500.0,
            timestamp=datetime(2026, 2, 10, 14, 0, 0, tzinfo=timezone.utc),
        )
        result = sf.filter_by_trend(no_sig, [], period=50)
        assert result.type == SignalType.NO_SIGNAL


# ---------------------------------------------------------------------------
# Volume filter
# ---------------------------------------------------------------------------

class TestFilterByVolume:
    """Test volume filter."""

    def test_high_volume_passes(self, sf: SignalFilter):
        """Signal with volume above average * ratio should pass."""
        candles = [_candle(97_500.0, volume=5.0)] * 19 + [_candle(97_500.0, volume=10.0)]
        signal = _buy_signal()
        result = sf.filter_by_volume(signal, candles, min_ratio=1.5)
        assert result.type == SignalType.BUY

    def test_low_volume_blocked(self, sf: SignalFilter):
        """Signal with volume below average * ratio should be blocked."""
        candles = [_candle(97_500.0, volume=10.0)] * 19 + [_candle(97_500.0, volume=5.0)]
        signal = _buy_signal()
        result = sf.filter_by_volume(signal, candles, min_ratio=1.5)
        assert result.type == SignalType.NO_SIGNAL

    def test_single_candle_passes(self, sf: SignalFilter):
        """With only one candle, no comparison possible -> passes."""
        candles = [_candle(97_500.0, volume=1.0)]
        signal = _buy_signal()
        result = sf.filter_by_volume(signal, candles, min_ratio=1.5)
        assert result.type == SignalType.BUY


# ---------------------------------------------------------------------------
# Volatility filter
# ---------------------------------------------------------------------------

class TestFilterByVolatility:
    """Test volatility (ATR) filter."""

    def test_within_range_passes(self, sf: SignalFilter):
        """ATR within bounds should pass."""
        # Each candle has high-low = 200
        candles = [_candle(97_500.0, high=97_600.0, low=97_400.0)] * 20
        signal = _buy_signal()
        result = sf.filter_by_volatility(signal, candles, min_atr=100.0, max_atr=300.0)
        assert result.type == SignalType.BUY

    def test_too_volatile_blocked(self, sf: SignalFilter):
        """ATR above max should block."""
        candles = [_candle(97_500.0, high=98_000.0, low=97_000.0)] * 20
        signal = _buy_signal()
        # ATR = 1000, max_atr = 500
        result = sf.filter_by_volatility(signal, candles, max_atr=500.0)
        assert result.type == SignalType.NO_SIGNAL

    def test_too_quiet_blocked(self, sf: SignalFilter):
        """ATR below min should block."""
        candles = [_candle(97_500.0, high=97_510.0, low=97_490.0)] * 20
        signal = _buy_signal()
        # ATR = 20, min_atr = 100
        result = sf.filter_by_volatility(signal, candles, min_atr=100.0)
        assert result.type == SignalType.NO_SIGNAL

    def test_no_bounds_passes(self, sf: SignalFilter):
        """No min/max -> passes."""
        candles = [_candle(97_500.0)] * 20
        signal = _buy_signal()
        result = sf.filter_by_volatility(signal, candles)
        assert result.type == SignalType.BUY


# ---------------------------------------------------------------------------
# Time filter
# ---------------------------------------------------------------------------

class TestFilterByTime:
    """Test time-based filter."""

    def test_excluded_hour_blocked(self, sf: SignalFilter):
        """Signal during excluded hour should be blocked."""
        signal = _buy_signal(ts=datetime(2026, 2, 10, 3, 0, 0, tzinfo=timezone.utc))
        result = sf.filter_by_time(signal, excluded_hours=[0, 1, 2, 3, 4, 5])
        assert result.type == SignalType.NO_SIGNAL

    def test_allowed_hour_passes(self, sf: SignalFilter):
        """Signal during allowed hour should pass."""
        signal = _buy_signal(ts=datetime(2026, 2, 10, 14, 0, 0, tzinfo=timezone.utc))
        result = sf.filter_by_time(signal, excluded_hours=[0, 1, 2, 3, 4, 5])
        assert result.type == SignalType.BUY

    def test_no_excluded_hours_passes(self, sf: SignalFilter):
        """No excluded hours -> everything passes."""
        signal = _buy_signal()
        result = sf.filter_by_time(signal, excluded_hours=None)
        assert result.type == SignalType.BUY

    def test_empty_excluded_list_passes(self, sf: SignalFilter):
        signal = _buy_signal()
        result = sf.filter_by_time(signal, excluded_hours=[])
        assert result.type == SignalType.BUY


# ---------------------------------------------------------------------------
# Spread filter
# ---------------------------------------------------------------------------

class TestFilterBySpread:
    """Test spread filter."""

    def test_tight_spread_passes(self, sf: SignalFilter):
        signal = _buy_signal()
        result = sf.filter_by_spread(signal, bid=97_490.0, ask=97_510.0, max_spread_pct=0.1)
        # Spread = 20 / 97500 * 100 ~= 0.0205% < 0.1%
        assert result.type == SignalType.BUY

    def test_wide_spread_blocked(self, sf: SignalFilter):
        signal = _buy_signal()
        result = sf.filter_by_spread(signal, bid=97_000.0, ask=98_000.0, max_spread_pct=0.1)
        # Spread = 1000 / 97500 * 100 ~= 1.026% > 0.1%
        assert result.type == SignalType.NO_SIGNAL

    def test_zero_bid_passes(self, sf: SignalFilter):
        """Invalid bid/ask should pass (no crash)."""
        signal = _buy_signal()
        result = sf.filter_by_spread(signal, bid=0.0, ask=97_510.0, max_spread_pct=0.1)
        assert result.type == SignalType.BUY


# ---------------------------------------------------------------------------
# Consecutive filter
# ---------------------------------------------------------------------------

class TestFilterByConsecutive:
    """Test consecutive same-direction filter."""

    def test_too_many_same_direction_blocked(self, sf: SignalFilter):
        """3 consecutive BUY signals -> next BUY blocked."""
        recent = [_buy_signal()] * 3
        signal = _buy_signal()
        result = sf.filter_by_consecutive(signal, recent, max_same=3)
        assert result.type == SignalType.NO_SIGNAL

    def test_mixed_directions_passes(self, sf: SignalFilter):
        """Mixed signals -> BUY allowed."""
        recent = [_buy_signal(), _sell_signal(), _buy_signal()]
        signal = _buy_signal()
        result = sf.filter_by_consecutive(signal, recent, max_same=3)
        assert result.type == SignalType.BUY

    def test_not_enough_history_passes(self, sf: SignalFilter):
        """Fewer recent signals than max_same -> passes."""
        recent = [_buy_signal()]
        signal = _buy_signal()
        result = sf.filter_by_consecutive(signal, recent, max_same=3)
        assert result.type == SignalType.BUY

    def test_empty_history_passes(self, sf: SignalFilter):
        signal = _buy_signal()
        result = sf.filter_by_consecutive(signal, [], max_same=3)
        assert result.type == SignalType.BUY


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------

class TestApplyFilters:
    """Test the master filter chain."""

    def test_all_pass(self, sf: SignalFilter):
        """When all filters pass, signal is returned."""
        candles = _candles_with_trend(count=60)
        signal = _buy_signal(price=candles[-1].close + 200)
        config = {
            "trend": {"period": 50},
        }
        result = sf.apply_filters(signal, candles, config)
        assert result.type == SignalType.BUY

    def test_first_failure_blocks(self, sf: SignalFilter):
        """The first failing filter should block the signal."""
        candles = _candles_with_trend(count=60)
        sma = sum(c.close for c in candles[-50:]) / 50
        signal = _buy_signal(price=sma - 500)
        config = {
            "trend": {"period": 50},
            "volume": {"min_ratio": 1.5},
        }
        result = sf.apply_filters(signal, candles, config)
        assert result.type == SignalType.NO_SIGNAL

    def test_no_config_passes(self, sf: SignalFilter):
        """Empty config means no filters applied."""
        signal = _buy_signal()
        result = sf.apply_filters(signal, [], {})
        assert result.type == SignalType.BUY

    def test_no_signal_passthrough(self, sf: SignalFilter):
        """NO_SIGNAL should not be filtered."""
        no_sig = Signal(
            type=SignalType.NO_SIGNAL,
            pair="BTC/USDT", timeframe="5m", price=97_500.0,
            timestamp=datetime(2026, 2, 10, 14, 0, 0, tzinfo=timezone.utc),
        )
        result = sf.apply_filters(no_sig, [], {"trend": {"period": 50}})
        assert result.type == SignalType.NO_SIGNAL

    def test_time_filter_in_chain(self, sf: SignalFilter):
        """Time filter blocking within apply_filters."""
        signal = _buy_signal(ts=datetime(2026, 2, 10, 3, 0, 0, tzinfo=timezone.utc))
        config = {"time": {"excluded_hours": [0, 1, 2, 3, 4, 5]}}
        result = sf.apply_filters(signal, [], config)
        assert result.type == SignalType.NO_SIGNAL


# ---------------------------------------------------------------------------
# Legacy check_all API
# ---------------------------------------------------------------------------

class TestCheckAll:
    """Test backward-compatible check_all method."""

    def test_empty_filters_passes(self, sf: SignalFilter):
        config = StrategyConfig(name="test", filters={})
        passed, reason = sf.check_all(config, {})
        assert passed is True

    def test_ema_trend_blocks(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"ema_trend": {"enabled": True}},
        )
        context = {"price": 97_000.0, "ema_trend_value": 98_000.0}
        passed, reason = sf.check_all(config, context)
        assert passed is False
        assert "EMA" in reason

    def test_trading_hours_blocks(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"trading_hours": {"start_hour": 8, "end_hour": 22}},
        )
        context = {"timestamp": datetime(2026, 2, 10, 3, 0, 0, tzinfo=timezone.utc)}
        passed, reason = sf.check_all(config, context)
        assert passed is False
        assert "hours" in reason.lower()

    def test_trading_hours_passes(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"trading_hours": {"start_hour": 8, "end_hour": 22}},
        )
        context = {"timestamp": datetime(2026, 2, 10, 14, 0, 0, tzinfo=timezone.utc)}
        passed, _ = sf.check_all(config, context)
        assert passed is True

    def test_loss_cooldown_blocks(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"loss_cooldown": {"cooldown_minutes": 15}},
        )
        now = datetime(2026, 2, 10, 14, 30, 0, tzinfo=timezone.utc)
        last_loss = now - timedelta(minutes=5)
        context = {"timestamp": now, "last_loss_time": last_loss}
        passed, reason = sf.check_all(config, context)
        assert passed is False
        assert "cooldown" in reason.lower()

    def test_loss_cooldown_passes_after_delay(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"loss_cooldown": {"cooldown_minutes": 15}},
        )
        now = datetime(2026, 2, 10, 14, 30, 0, tzinfo=timezone.utc)
        last_loss = now - timedelta(minutes=20)
        context = {"timestamp": now, "last_loss_time": last_loss}
        passed, _ = sf.check_all(config, context)
        assert passed is True

    def test_max_daily_trades_blocks(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"max_daily_trades": {"max_trades": 5}},
        )
        context = {"daily_trade_count": 5}
        passed, reason = sf.check_all(config, context)
        assert passed is False
        assert "daily trades" in reason.lower()

    def test_max_daily_loss_blocks(self, sf: SignalFilter):
        config = StrategyConfig(
            name="test",
            filters={"max_daily_loss": {"max_loss_pct": 3.0}},
        )
        context = {"daily_pnl_pct": -3.5}
        passed, reason = sf.check_all(config, context)
        assert passed is False
        assert "daily loss" in reason.lower()

    def test_disabled_filter_skipped(self, sf: SignalFilter):
        """Filter with enabled=False should be skipped."""
        config = StrategyConfig(
            name="test",
            filters={"ema_trend": {"enabled": False}},
        )
        context = {"price": 97_000.0, "ema_trend_value": 98_000.0}
        passed, _ = sf.check_all(config, context)
        assert passed is True
