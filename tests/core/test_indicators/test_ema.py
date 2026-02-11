"""Tests for the EMA (Exponential Moving Average) indicator.

These tests validate the EMA implementation once built. Tests that
depend on unimplemented methods are skipped with a clear reason.
"""

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


@pytest.mark.skip(reason="EMA.calculate() not implemented yet")
def test_ema_calculate(ema_indicator, sample_candles):
    """EMA calculation over a candle history should return a values list."""
    result = ema_indicator.calculate(sample_candles, period=20)
    assert "ema" in result
    ema_values = result["ema"]
    assert len(ema_values) == len(sample_candles)
    # First (period - 1) values may be None/NaN
    assert ema_values[-1] is not None
    # EMA should be close to the last close price
    assert abs(ema_values[-1] - sample_candles[-1].close) < sample_candles[-1].close * 0.05


@pytest.mark.skip(reason="EMA.update() not implemented yet")
def test_ema_update_incremental(ema_indicator, sample_candles):
    """Incremental update should produce the same result as full calculate."""
    # Full calculation
    full_state = ema_indicator.calculate(sample_candles[:-1], period=20)

    # Incremental update with the last candle
    updated_state = ema_indicator.update(sample_candles[-1], full_state, period=20)
    assert "ema" in updated_state

    # Full calculation including the last candle
    full_with_last = ema_indicator.calculate(sample_candles, period=20)

    # The latest EMA value should match
    assert updated_state["ema"][-1] == pytest.approx(full_with_last["ema"][-1], rel=1e-6)


@pytest.mark.skip(reason="EMA.evaluate() not implemented yet")
def test_ema_evaluate_price_above(ema_indicator, sample_candles):
    """evaluate with 'price_above' should return True when close > EMA."""
    state = ema_indicator.calculate(sample_candles, period=20)
    # Inject a close price well above the EMA
    state["current_close"] = state["ema"][-1] * 1.05
    assert ema_indicator.evaluate(state, "price_above") is True


@pytest.mark.skip(reason="EMA.evaluate() not implemented yet")
def test_ema_evaluate_price_below(ema_indicator, sample_candles):
    """evaluate with 'price_below' should return True when close < EMA."""
    state = ema_indicator.calculate(sample_candles, period=20)
    # Inject a close price well below the EMA
    state["current_close"] = state["ema"][-1] * 0.95
    assert ema_indicator.evaluate(state, "price_below") is True
