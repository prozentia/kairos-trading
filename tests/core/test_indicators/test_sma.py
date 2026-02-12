"""Tests for the SMA (Simple Moving Average) indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def sma_indicator():
    """Return the registered SMA indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("sma")


def test_sma_registered(sma_indicator):
    """SMA should be registered with correct attributes."""
    assert sma_indicator.key == "sma"
    assert sma_indicator.category == "trend"
    assert sma_indicator.name == "Simple Moving Average"


def test_sma_default_params(sma_indicator):
    """SMA should have default period=20 and source=close."""
    assert sma_indicator.default_params["period"] == 20
    assert sma_indicator.default_params["source"] == "close"


def test_sma_calculate_structure(sma_indicator, sample_candles):
    """calculate() should return a dict with sma list of correct length."""
    result = sma_indicator.calculate(sample_candles, period=20)
    assert "sma" in result
    assert "period" in result
    assert len(result["sma"]) == len(sample_candles)


def test_sma_calculate_none_before_period(sma_indicator, sample_candles):
    """First period-1 SMA values should be None."""
    result = sma_indicator.calculate(sample_candles, period=20)
    for i in range(18):
        assert result["sma"][i] is None
    assert result["sma"][19] is not None


def test_sma_calculate_first_value_is_mean(sma_indicator, sample_candles):
    """The first SMA value should be the mean of the first period closes."""
    period = 10
    result = sma_indicator.calculate(sample_candles, period=period)
    expected = sum(c.close for c in sample_candles[:period]) / period
    assert result["sma"][period - 1] == pytest.approx(expected, rel=1e-6)


def test_sma_calculate_values_reasonable(sma_indicator, sample_candles):
    """SMA values should be close to actual close prices."""
    result = sma_indicator.calculate(sample_candles, period=20)
    last_sma = result["sma"][-1]
    last_close = sample_candles[-1].close
    assert last_sma is not None
    assert abs(last_sma - last_close) < last_close * 0.05


def test_sma_calculate_insufficient_candles(sma_indicator, sample_candles):
    """With fewer candles than period, all values should be None."""
    result = sma_indicator.calculate(sample_candles[:5], period=20)
    assert all(v is None for v in result["sma"])


def test_sma_update_incremental(sma_indicator, sample_candles):
    """Incremental update should match full calculation."""
    full_state = sma_indicator.calculate(sample_candles[:-1], period=20)
    updated_state = sma_indicator.update(sample_candles[-1], full_state, period=20)

    full_with_last = sma_indicator.calculate(sample_candles, period=20)

    assert updated_state["sma"][-1] == pytest.approx(
        full_with_last["sma"][-1], rel=1e-6
    )


def test_sma_evaluate_price_above(sma_indicator, sample_candles):
    """price_above should be True when close > SMA."""
    state = sma_indicator.calculate(sample_candles, period=20)
    state["current_close"] = state["sma"][-1] * 1.05
    assert sma_indicator.evaluate(state, "price_above") is True


def test_sma_evaluate_price_below(sma_indicator, sample_candles):
    """price_below should be True when close < SMA."""
    state = sma_indicator.calculate(sample_candles, period=20)
    state["current_close"] = state["sma"][-1] * 0.95
    assert sma_indicator.evaluate(state, "price_below") is True


def test_sma_evaluate_rising(sma_indicator, sample_candles):
    """rising should return a bool."""
    state = sma_indicator.calculate(sample_candles, period=20)
    result = sma_indicator.evaluate(state, "rising")
    assert isinstance(result, bool)


def test_sma_evaluate_falling(sma_indicator, sample_candles):
    """falling should return a bool."""
    state = sma_indicator.calculate(sample_candles, period=20)
    result = sma_indicator.evaluate(state, "falling")
    assert isinstance(result, bool)


def test_sma_evaluate_unknown_operator(sma_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = sma_indicator.calculate(sample_candles, period=20)
    with pytest.raises(ValueError, match="Unknown operator"):
        sma_indicator.evaluate(state, "invalid_op")


def test_sma_evaluate_empty_state(sma_indicator):
    """Evaluate on empty state should return False."""
    state = {"sma": [], "current_close": 0.0}
    assert sma_indicator.evaluate(state, "price_above") is False
