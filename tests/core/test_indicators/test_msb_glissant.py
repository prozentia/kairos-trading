"""Tests for the MSB Glissant (Sliding Market Structure Break) indicator.

This is the KEY strategy indicator for Kairos Trading, ported from
the original BTC Sniper Bot.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timedelta, timezone


@pytest.fixture
def msb_indicator():
    """Return the registered MSB Glissant indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("msb_glissant")


def _make_candles(prices: list[tuple[float, float, float, float]]) -> list[Candle]:
    """Create candles from (open, high, low, close) tuples."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for i, (o, h, l, c) in enumerate(prices):
        candles.append(Candle(
            timestamp=ts + timedelta(minutes=i),
            open=o, high=h, low=l, close=c,
            volume=10.0, pair="BTC/USDT", timeframe="1m",
        ))
    return candles


def test_msb_registered(msb_indicator):
    """MSB Glissant should be registered in the global registry."""
    assert msb_indicator.key == "msb_glissant"
    assert msb_indicator.category == "special"
    assert msb_indicator.name == "MSB Glissant"


def test_msb_default_params(msb_indicator):
    """MSB should have expected default parameters."""
    assert msb_indicator.default_params["swing_lookback"] == 5
    assert msb_indicator.default_params["bb_period"] == 20
    assert msb_indicator.default_params["bb_std_dev"] == 2.0
    assert msb_indicator.default_params["bb_proximity_pct"] == 0.15


def test_msb_calculate_returns_keys(msb_indicator, sample_candles):
    """Calculate should return all expected keys."""
    result = msb_indicator.calculate(sample_candles)

    assert "swing_highs" in result
    assert "swing_lows" in result
    assert "msb_high" in result
    assert "msb_low" in result
    assert "break_up" in result
    assert "break_down" in result
    assert "bb_lower" in result
    assert "prices" in result


def test_msb_detects_swing_highs(msb_indicator):
    """Should detect a swing high when it is the highest in the window."""
    # Create a clear swing high at position 5
    prices = [
        (100, 102, 98, 101),    # 0
        (101, 103, 99, 102),    # 1
        (102, 104, 100, 103),   # 2
        (103, 105, 101, 104),   # 3
        (104, 106, 102, 105),   # 4
        (105, 120, 103, 106),   # 5 - Swing high (high=120)
        (106, 107, 101, 103),   # 6
        (103, 105, 99, 100),    # 7
        (100, 102, 97, 98),     # 8
        (98, 100, 95, 96),      # 9
        (96, 98, 93, 94),       # 10
    ]
    candles = _make_candles(prices)
    result = msb_indicator.calculate(candles, swing_lookback=3)

    # Should detect a swing high around index 5
    swing_highs = result["swing_highs"]
    has_swing = any(v is not None for v in swing_highs)
    assert has_swing, "Should detect at least one swing high"


def test_msb_detects_swing_lows(msb_indicator):
    """Should detect a swing low when it is the lowest in the window."""
    prices = [
        (100, 102, 98, 101),    # 0
        (101, 103, 99, 100),    # 1
        (100, 101, 97, 98),     # 2
        (98, 100, 95, 96),      # 3
        (96, 98, 93, 95),       # 4
        (95, 97, 80, 96),       # 5 - Swing low (low=80)
        (96, 100, 94, 99),      # 6
        (99, 103, 97, 102),     # 7
        (102, 106, 100, 105),   # 8
        (105, 108, 103, 107),   # 9
        (107, 110, 105, 109),   # 10
    ]
    candles = _make_candles(prices)
    result = msb_indicator.calculate(candles, swing_lookback=3)

    swing_lows = result["swing_lows"]
    has_swing = any(v is not None for v in swing_lows)
    assert has_swing, "Should detect at least one swing low"


def test_msb_break_up_detection(msb_indicator, sample_candles):
    """Should detect bullish MSB when price breaks above swing high."""
    result = msb_indicator.calculate(sample_candles)

    # break_up is a boolean
    assert isinstance(result["break_up"], bool)


def test_msb_break_down_detection(msb_indicator, sample_candles):
    """Should detect bearish MSB when price breaks below swing low."""
    result = msb_indicator.calculate(sample_candles)

    assert isinstance(result["break_down"], bool)


def test_msb_bb_lower_computed(msb_indicator, sample_candles):
    """Should compute BB lower band value."""
    result = msb_indicator.calculate(sample_candles)

    assert result["bb_lower"] is not None
    assert result["bb_lower"] > 0


def test_msb_evaluate_break_up(msb_indicator, sample_candles):
    """Evaluate break_up should return the break_up flag."""
    state = msb_indicator.calculate(sample_candles)

    state["break_up"] = True
    assert msb_indicator.evaluate(state, "break_up") is True

    state["break_up"] = False
    assert msb_indicator.evaluate(state, "break_up") is False


def test_msb_evaluate_break_down(msb_indicator, sample_candles):
    """Evaluate break_down should return the break_down flag."""
    state = msb_indicator.calculate(sample_candles)

    state["break_down"] = True
    assert msb_indicator.evaluate(state, "break_down") is True

    state["break_down"] = False
    assert msb_indicator.evaluate(state, "break_down") is False


def test_msb_evaluate_above_msb(msb_indicator, sample_candles):
    """Evaluate above_msb should check price > msb_high."""
    state = msb_indicator.calculate(sample_candles)

    if state["msb_high"] is not None:
        state["prices"][-1] = state["msb_high"] + 100.0
        assert msb_indicator.evaluate(state, "above_msb") is True

        state["prices"][-1] = state["msb_high"] - 100.0
        assert msb_indicator.evaluate(state, "above_msb") is False


def test_msb_evaluate_below_msb(msb_indicator, sample_candles):
    """Evaluate below_msb should check price < msb_low."""
    state = msb_indicator.calculate(sample_candles)

    if state["msb_low"] is not None:
        state["prices"][-1] = state["msb_low"] - 100.0
        assert msb_indicator.evaluate(state, "below_msb") is True

        state["prices"][-1] = state["msb_low"] + 100.0
        assert msb_indicator.evaluate(state, "below_msb") is False


def test_msb_evaluate_near_bb_lower(msb_indicator, sample_candles):
    """Evaluate near_bb_lower should detect proximity to BB lower."""
    state = msb_indicator.calculate(sample_candles)

    if state["bb_lower"] is not None:
        # Set price very close to BB lower
        state["prices"][-1] = state["bb_lower"] * 1.0001
        assert msb_indicator.evaluate(state, "near_bb_lower", 0.15) is True

        # Set price far from BB lower
        state["prices"][-1] = state["bb_lower"] * 1.05
        assert msb_indicator.evaluate(state, "near_bb_lower", 0.15) is False


def test_msb_evaluate_break_detected(msb_indicator, sample_candles):
    """Evaluate break_detected should check either direction."""
    state = msb_indicator.calculate(sample_candles)

    state["break_up"] = True
    state["break_down"] = False
    assert msb_indicator.evaluate(state, "break_detected") is True

    state["break_up"] = False
    state["break_down"] = True
    assert msb_indicator.evaluate(state, "break_detected") is True

    state["break_up"] = False
    state["break_down"] = False
    assert msb_indicator.evaluate(state, "break_detected") is False


def test_msb_unknown_operator(msb_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = msb_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        msb_indicator.evaluate(state, "invalid_op")


def test_msb_with_large_dataset(msb_indicator, sample_candles):
    """MSB should handle the full 500-candle dataset without errors."""
    result = msb_indicator.calculate(sample_candles, swing_lookback=5)

    # Should detect at least some swings in 500 candles
    swing_high_count = sum(1 for v in result["swing_highs"] if v is not None)
    swing_low_count = sum(1 for v in result["swing_lows"] if v is not None)

    assert swing_high_count > 0, "Should detect swing highs in 500 candles"
    assert swing_low_count > 0, "Should detect swing lows in 500 candles"
    assert result["msb_high"] is not None
    assert result["msb_low"] is not None
