"""Tests for the EMA (Exponential Moving Average) indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def ema_indicator():
    """Return the registered EMA indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("ema")


def test_ema_registered(ema_indicator):
    """EMA should be registered in the global registry."""
    assert ema_indicator.key == "ema"
    assert ema_indicator.category == "trend"
    assert ema_indicator.name == "Exponential Moving Average"


def test_ema_default_params(ema_indicator):
    """EMA should have default period=20 and source=close."""
    assert ema_indicator.default_params["period"] == 20
    assert ema_indicator.default_params["source"] == "close"


def test_ema_calculate_structure(ema_indicator, sample_candles):
    """calculate() should return a dict with ema list of correct length."""
    result = ema_indicator.calculate(sample_candles, period=20)
    assert "ema" in result
    assert "period" in result
    assert "current_close" in result
    assert len(result["ema"]) == len(sample_candles)


def test_ema_calculate_none_before_period(ema_indicator, sample_candles):
    """First period-1 EMA values should be None."""
    result = ema_indicator.calculate(sample_candles, period=20)
    for i in range(18):
        assert result["ema"][i] is None
    # Value at index period-1 (19) should be the SMA seed
    assert result["ema"][19] is not None


def test_ema_calculate_values_reasonable(ema_indicator, sample_candles):
    """EMA values should be close to actual close prices."""
    result = ema_indicator.calculate(sample_candles, period=20)
    ema_values = result["ema"]
    last_ema = ema_values[-1]
    last_close = sample_candles[-1].close
    # EMA should be within 5% of the last close
    assert last_ema is not None
    assert abs(last_ema - last_close) < last_close * 0.05


def test_ema_calculate_no_none_after_period(ema_indicator, sample_candles):
    """All EMA values after period-1 should be non-None."""
    result = ema_indicator.calculate(sample_candles, period=20)
    for i in range(19, len(sample_candles)):
        assert result["ema"][i] is not None


def test_ema_calculate_insufficient_candles(ema_indicator, sample_candles):
    """With fewer candles than period, all values should be None."""
    result = ema_indicator.calculate(sample_candles[:10], period=20)
    assert all(v is None for v in result["ema"])


def test_ema_update_incremental(ema_indicator, sample_candles):
    """Incremental update should produce the same result as full calculate."""
    full_state = ema_indicator.calculate(sample_candles[:-1], period=20)
    updated_state = ema_indicator.update(sample_candles[-1], full_state, period=20)

    full_with_last = ema_indicator.calculate(sample_candles, period=20)

    assert updated_state["ema"][-1] == pytest.approx(
        full_with_last["ema"][-1], rel=1e-6
    )


def test_ema_evaluate_price_above(ema_indicator, sample_candles):
    """price_above should return True when close > EMA."""
    state = ema_indicator.calculate(sample_candles, period=20)
    state["current_close"] = state["ema"][-1] * 1.05
    assert ema_indicator.evaluate(state, "price_above") is True


def test_ema_evaluate_price_below(ema_indicator, sample_candles):
    """price_below should return True when close < EMA."""
    state = ema_indicator.calculate(sample_candles, period=20)
    state["current_close"] = state["ema"][-1] * 0.95
    assert ema_indicator.evaluate(state, "price_below") is True


def test_ema_evaluate_rising(ema_indicator, sample_candles):
    """rising should check if the latest EMA > previous EMA."""
    state = ema_indicator.calculate(sample_candles, period=20)
    result = ema_indicator.evaluate(state, "rising")
    # Just check it returns a bool without error
    assert isinstance(result, bool)


def test_ema_evaluate_falling(ema_indicator, sample_candles):
    """falling should check if the latest EMA < previous EMA."""
    state = ema_indicator.calculate(sample_candles, period=20)
    result = ema_indicator.evaluate(state, "falling")
    assert isinstance(result, bool)


def test_ema_evaluate_unknown_operator(ema_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = ema_indicator.calculate(sample_candles, period=20)
    with pytest.raises(ValueError, match="Unknown operator"):
        ema_indicator.evaluate(state, "invalid_op")


def test_ema_evaluate_empty_state(ema_indicator):
    """Evaluate on empty state should return False gracefully."""
    state = {"ema": [], "current_close": 0.0}
    assert ema_indicator.evaluate(state, "price_above") is False
