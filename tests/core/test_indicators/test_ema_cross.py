"""Tests for the EMA Crossover indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def ema_cross_indicator():
    """Return the registered EMA Cross indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("ema_cross")


def test_ema_cross_registered(ema_cross_indicator):
    """EMA Cross should be registered with correct attributes."""
    assert ema_cross_indicator.key == "ema_cross"
    assert ema_cross_indicator.category == "trend"
    assert ema_cross_indicator.name == "EMA Crossover"


def test_ema_cross_default_params(ema_cross_indicator):
    """Default params should have fast=9 and slow=21."""
    assert ema_cross_indicator.default_params["fast_period"] == 9
    assert ema_cross_indicator.default_params["slow_period"] == 21


def test_ema_cross_calculate_structure(ema_cross_indicator, sample_candles):
    """calculate() should return fast_ema and slow_ema lists."""
    result = ema_cross_indicator.calculate(sample_candles)
    assert "fast_ema" in result
    assert "slow_ema" in result
    assert len(result["fast_ema"]) == len(sample_candles)
    assert len(result["slow_ema"]) == len(sample_candles)


def test_ema_cross_fast_starts_before_slow(ema_cross_indicator, sample_candles):
    """Fast EMA should have valid values earlier than slow EMA."""
    result = ema_cross_indicator.calculate(sample_candles, fast_period=9, slow_period=21)
    # Fast EMA first valid at index 8, slow at index 20
    assert result["fast_ema"][8] is not None
    assert result["slow_ema"][8] is None
    assert result["slow_ema"][20] is not None


def test_ema_cross_values_reasonable(ema_cross_indicator, sample_candles):
    """Both EMAs should be within reasonable range of close prices."""
    result = ema_cross_indicator.calculate(sample_candles)
    last_close = sample_candles[-1].close
    fast = result["fast_ema"][-1]
    slow = result["slow_ema"][-1]
    assert fast is not None
    assert slow is not None
    assert abs(fast - last_close) < last_close * 0.05
    assert abs(slow - last_close) < last_close * 0.05


def test_ema_cross_update_incremental(ema_cross_indicator, sample_candles):
    """Incremental update should match full calculation."""
    state = ema_cross_indicator.calculate(sample_candles[:-1])
    updated = ema_cross_indicator.update(sample_candles[-1], state)

    full = ema_cross_indicator.calculate(sample_candles)

    assert updated["fast_ema"][-1] == pytest.approx(full["fast_ema"][-1], rel=1e-6)
    assert updated["slow_ema"][-1] == pytest.approx(full["slow_ema"][-1], rel=1e-6)


def test_ema_cross_evaluate_bullish(ema_cross_indicator, sample_candles):
    """bullish should be True when fast > slow."""
    state = ema_cross_indicator.calculate(sample_candles)
    fast = state["fast_ema"][-1]
    slow = state["slow_ema"][-1]
    expected = fast > slow
    assert ema_cross_indicator.evaluate(state, "bullish") == expected


def test_ema_cross_evaluate_bearish(ema_cross_indicator, sample_candles):
    """bearish should be True when fast < slow."""
    state = ema_cross_indicator.calculate(sample_candles)
    fast = state["fast_ema"][-1]
    slow = state["slow_ema"][-1]
    expected = fast < slow
    assert ema_cross_indicator.evaluate(state, "bearish") == expected


def test_ema_cross_evaluate_golden_cross(ema_cross_indicator, sample_candles):
    """golden_cross should return a bool without error."""
    state = ema_cross_indicator.calculate(sample_candles)
    result = ema_cross_indicator.evaluate(state, "golden_cross")
    assert isinstance(result, bool)


def test_ema_cross_evaluate_death_cross(ema_cross_indicator, sample_candles):
    """death_cross should return a bool without error."""
    state = ema_cross_indicator.calculate(sample_candles)
    result = ema_cross_indicator.evaluate(state, "death_cross")
    assert isinstance(result, bool)


def test_ema_cross_evaluate_unknown_operator(ema_cross_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = ema_cross_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        ema_cross_indicator.evaluate(state, "invalid_op")


def test_ema_cross_evaluate_empty_state(ema_cross_indicator):
    """Evaluate on empty state should return False."""
    state = {"fast_ema": [], "slow_ema": []}
    assert ema_cross_indicator.evaluate(state, "bullish") is False


def test_ema_cross_insufficient_candles(ema_cross_indicator, sample_candles):
    """With fewer candles than slow period, slow EMA should be all None."""
    result = ema_cross_indicator.calculate(sample_candles[:10], slow_period=21)
    assert all(v is None for v in result["slow_ema"])
