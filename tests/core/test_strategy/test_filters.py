"""Tests for post-signal filters.

Filters run after a signal is generated to decide whether it should be
forwarded to the engine (e.g. trend confirmation, time restrictions,
cooldown after loss). All tests are skipped until filters are implemented.
"""

from datetime import datetime, timezone

import pytest

from core.models import Signal, SignalType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _buy_signal(price: float = 97_500.0) -> Signal:
    """Create a BUY signal for testing."""
    return Signal(
        type=SignalType.BUY,
        pair="BTC/USDT",
        timeframe="1m",
        price=price,
        timestamp=datetime(2026, 2, 10, 14, 30, 0, tzinfo=timezone.utc),
        strategy_name="test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Filters not implemented yet")
def test_ema_trend_filter_blocks_buy():
    """EMA trend filter should block BUY when price is below EMA 50."""
    signal = _buy_signal(price=97_500.0)
    ema_state = {"ema": [None] * 49 + [98_000.0]}  # EMA is above price

    # filter_config = {"indicator": "ema", "params": {"period": 50}, "operator": "price_above"}
    # result = ema_trend_filter(signal, ema_state, filter_config)
    # assert result is None  # blocked


@pytest.mark.skip(reason="Filters not implemented yet")
def test_ema_trend_filter_passes():
    """EMA trend filter should pass BUY when price is above EMA 50."""
    signal = _buy_signal(price=98_500.0)
    ema_state = {"ema": [None] * 49 + [98_000.0]}  # EMA is below price

    # filter_config = {"indicator": "ema", "params": {"period": 50}, "operator": "price_above"}
    # result = ema_trend_filter(signal, ema_state, filter_config)
    # assert result is not None  # passed
    # assert result.type == SignalType.BUY


@pytest.mark.skip(reason="Filters not implemented yet")
def test_trading_hours_filter():
    """Trading hours filter should block signals outside allowed hours."""
    # Signal at 14:30 UTC
    signal = _buy_signal()

    # Allowed: 08:00 to 22:00 UTC -> should pass
    # filter_config = {"start": "08:00", "end": "22:00", "timezone": "UTC"}
    # assert trading_hours_filter(signal, filter_config) is not None

    # Signal at 03:00 UTC -> outside hours -> should block
    late_signal = Signal(
        type=SignalType.BUY,
        pair="BTC/USDT",
        timeframe="1m",
        price=97_500.0,
        timestamp=datetime(2026, 2, 10, 3, 0, 0, tzinfo=timezone.utc),
        strategy_name="test",
    )
    # assert trading_hours_filter(late_signal, filter_config) is None


@pytest.mark.skip(reason="Filters not implemented yet")
def test_loss_cooldown_filter():
    """Cooldown filter should block new signals for N minutes after a loss."""
    signal = _buy_signal()

    # Last trade was a loss 5 minutes ago, cooldown is 15 minutes
    # filter_state = {
    #     "last_loss_time": datetime(2026, 2, 10, 14, 25, 0, tzinfo=timezone.utc),
    #     "cooldown_minutes": 15,
    # }
    # assert loss_cooldown_filter(signal, filter_state) is None  # blocked

    # After cooldown period has elapsed
    # filter_state["last_loss_time"] = datetime(2026, 2, 10, 14, 0, 0, tzinfo=timezone.utc)
    # assert loss_cooldown_filter(signal, filter_state) is not None  # passed


@pytest.mark.skip(reason="Filters not implemented yet")
def test_all_filters_pass():
    """When all filters pass, the signal should be forwarded unchanged."""
    signal = _buy_signal()

    # Simulate a filter chain where all filters pass
    # filters = [ema_trend_filter, trading_hours_filter, loss_cooldown_filter]
    # result = apply_filters(signal, filters, indicator_states, filter_configs)
    # assert result is not None
    # assert result.type == SignalType.BUY
    # assert result.pair == signal.pair
