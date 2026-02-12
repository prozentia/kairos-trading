"""Tests for the ATR (Average True Range) indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timezone


@pytest.fixture
def atr_indicator():
    """Return the registered ATR indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("atr")


def test_atr_registered(atr_indicator):
    """ATR should be registered in the global registry."""
    assert atr_indicator.key == "atr"
    assert atr_indicator.category == "volatility"
    assert atr_indicator.name == "Average True Range"


def test_atr_default_params(atr_indicator):
    """ATR should have default period=14."""
    assert atr_indicator.default_params["period"] == 14


def test_atr_calculate_returns_keys(atr_indicator, sample_candles):
    """Calculate should return atr, tr, and prev_close."""
    result = atr_indicator.calculate(sample_candles, period=14)

    assert "atr" in result
    assert "tr" in result
    assert "prev_close" in result
    assert len(result["atr"]) == len(sample_candles)
    assert len(result["tr"]) == len(sample_candles)


def test_atr_warmup_period(atr_indicator, sample_candles):
    """ATR values should be None during warmup."""
    result = atr_indicator.calculate(sample_candles, period=14)

    # First 14 values should be None (indices 0..13)
    for i in range(14):
        assert result["atr"][i] is None

    # After warmup, ATR should be present
    assert result["atr"][14] is not None


def test_atr_values_positive(atr_indicator, sample_candles):
    """ATR values should always be positive."""
    result = atr_indicator.calculate(sample_candles, period=14)

    for val in result["atr"]:
        if val is not None:
            assert val > 0


def test_atr_true_range_positive(atr_indicator, sample_candles):
    """True range values should always be positive."""
    result = atr_indicator.calculate(sample_candles, period=14)

    for val in result["tr"]:
        if val is not None:
            assert val >= 0


def test_atr_manual_calculation(atr_indicator):
    """Verify ATR against manual calculation with known data."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    # Simple candles with known values
    data = [
        (100, 105, 95, 102, 1.0),
        (102, 108, 100, 106, 1.0),
        (106, 110, 104, 108, 1.0),
        (108, 112, 106, 110, 1.0),
        (110, 115, 108, 112, 1.0),
    ]
    for i, (o, h, l, c, v) in enumerate(data):
        from datetime import timedelta
        candles.append(Candle(
            timestamp=ts + timedelta(minutes=i),
            open=o, high=h, low=l, close=c,
            volume=v, pair="TEST/USDT", timeframe="1m",
        ))

    result = atr_indicator.calculate(candles, period=3)

    # First TR = 105 - 95 = 10
    assert result["tr"][0] == 10.0

    # TR[1] = max(108-100, |108-102|, |100-102|) = max(8, 6, 2) = 8
    assert result["tr"][1] == 8.0

    # ATR values should exist after period
    assert result["atr"][3] is not None


def test_atr_update_matches_calculate(atr_indicator, sample_candles):
    """Incremental update should match full calculation."""
    full = atr_indicator.calculate(sample_candles, period=14)

    partial = atr_indicator.calculate(sample_candles[:-1], period=14)
    updated = atr_indicator.update(sample_candles[-1], partial, period=14)

    assert updated["atr"][-1] == pytest.approx(full["atr"][-1], rel=1e-6)


def test_atr_evaluate_above(atr_indicator, sample_candles):
    """Evaluate 'above' should check ATR > value."""
    state = atr_indicator.calculate(sample_candles, period=14)
    atr_val = state["atr"][-1]

    assert atr_indicator.evaluate(state, "above", atr_val - 1.0) is True
    assert atr_indicator.evaluate(state, "above", atr_val + 1.0) is False


def test_atr_evaluate_below(atr_indicator, sample_candles):
    """Evaluate 'below' should check ATR < value."""
    state = atr_indicator.calculate(sample_candles, period=14)
    atr_val = state["atr"][-1]

    assert atr_indicator.evaluate(state, "below", atr_val + 1.0) is True
    assert atr_indicator.evaluate(state, "below", atr_val - 1.0) is False


def test_atr_evaluate_rising(atr_indicator, sample_candles):
    """Evaluate 'rising' should detect increasing ATR."""
    state = atr_indicator.calculate(sample_candles, period=14)

    # Force a rising ATR
    last_valid = None
    for i in range(len(state["atr"]) - 1, -1, -1):
        if state["atr"][i] is not None:
            if last_valid is None:
                last_valid = i
            else:
                state["atr"][i] = state["atr"][last_valid] - 10.0
                break

    assert atr_indicator.evaluate(state, "rising") is True


def test_atr_evaluate_falling(atr_indicator, sample_candles):
    """Evaluate 'falling' should detect decreasing ATR."""
    state = atr_indicator.calculate(sample_candles, period=14)

    # Force a falling ATR
    last_valid = None
    for i in range(len(state["atr"]) - 1, -1, -1):
        if state["atr"][i] is not None:
            if last_valid is None:
                last_valid = i
            else:
                state["atr"][i] = state["atr"][last_valid] + 10.0
                break

    assert atr_indicator.evaluate(state, "falling") is True


def test_atr_unknown_operator(atr_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = atr_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        atr_indicator.evaluate(state, "invalid_op")
