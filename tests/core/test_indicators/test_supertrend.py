"""Tests for the Supertrend indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def supertrend_indicator():
    """Return the registered Supertrend indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("supertrend")


def test_supertrend_registered(supertrend_indicator):
    """Supertrend should be registered with correct attributes."""
    assert supertrend_indicator.key == "supertrend"
    assert supertrend_indicator.category == "trend"
    assert supertrend_indicator.name == "Supertrend"


def test_supertrend_default_params(supertrend_indicator):
    """Default params should be period=10, multiplier=3.0."""
    assert supertrend_indicator.default_params["period"] == 10
    assert supertrend_indicator.default_params["multiplier"] == 3.0


def test_supertrend_calculate_structure(supertrend_indicator, sample_candles):
    """calculate() should return all expected keys."""
    result = supertrend_indicator.calculate(sample_candles)
    assert "supertrend" in result
    assert "direction" in result
    assert "atr" in result
    assert "upper_band" in result
    assert "lower_band" in result
    assert len(result["supertrend"]) == len(sample_candles)
    assert len(result["direction"]) == len(sample_candles)


def test_supertrend_none_before_period(supertrend_indicator, sample_candles):
    """Values before the period should be None."""
    result = supertrend_indicator.calculate(sample_candles, period=10)
    for i in range(9):
        assert result["supertrend"][i] is None
        assert result["direction"][i] is None


def test_supertrend_has_values_after_period(supertrend_indicator, sample_candles):
    """After the warmup period, values should exist."""
    result = supertrend_indicator.calculate(sample_candles, period=10)
    # Check the last value
    assert result["supertrend"][-1] is not None
    assert result["direction"][-1] in (1, -1)


def test_supertrend_direction_values(supertrend_indicator, sample_candles):
    """Direction should only be +1 or -1 (or None)."""
    result = supertrend_indicator.calculate(sample_candles)
    for d in result["direction"]:
        assert d is None or d in (1, -1)


def test_supertrend_value_reasonable(supertrend_indicator, sample_candles):
    """Supertrend value should be in a reasonable range of close prices."""
    result = supertrend_indicator.calculate(sample_candles)
    st = result["supertrend"][-1]
    close = sample_candles[-1].close
    assert st is not None
    # Should be within 5% of close
    assert abs(st - close) < close * 0.05


def test_supertrend_update_incremental(supertrend_indicator, sample_candles):
    """Incremental update should produce consistent direction."""
    state = supertrend_indicator.calculate(sample_candles[:-1])
    updated = supertrend_indicator.update(sample_candles[-1], state)

    full = supertrend_indicator.calculate(sample_candles)

    # Direction should match
    assert updated["direction"][-1] == full["direction"][-1]


def test_supertrend_evaluate_uptrend(supertrend_indicator, sample_candles):
    """uptrend should return True when direction is +1."""
    state = supertrend_indicator.calculate(sample_candles)
    result = supertrend_indicator.evaluate(state, "uptrend")
    expected = state["direction"][-1] == 1
    assert result == expected


def test_supertrend_evaluate_downtrend(supertrend_indicator, sample_candles):
    """downtrend should return True when direction is -1."""
    state = supertrend_indicator.calculate(sample_candles)
    result = supertrend_indicator.evaluate(state, "downtrend")
    expected = state["direction"][-1] == -1
    assert result == expected


def test_supertrend_evaluate_flip_up(supertrend_indicator, sample_candles):
    """flip_up should return a bool."""
    state = supertrend_indicator.calculate(sample_candles)
    result = supertrend_indicator.evaluate(state, "flip_up")
    assert isinstance(result, bool)


def test_supertrend_evaluate_flip_down(supertrend_indicator, sample_candles):
    """flip_down should return a bool."""
    state = supertrend_indicator.calculate(sample_candles)
    result = supertrend_indicator.evaluate(state, "flip_down")
    assert isinstance(result, bool)


def test_supertrend_evaluate_unknown(supertrend_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = supertrend_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        supertrend_indicator.evaluate(state, "invalid_op")


def test_supertrend_insufficient_candles(supertrend_indicator, sample_candles):
    """With too few candles, all values should be None."""
    result = supertrend_indicator.calculate(sample_candles[:5], period=10)
    assert all(v is None for v in result["supertrend"])
