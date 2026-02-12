"""Tests for the RSI (Relative Strength Index) indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def rsi_indicator():
    """Return the registered RSI indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("rsi")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_rsi_registered(rsi_indicator):
    """RSI should be registered in the global registry."""
    assert rsi_indicator.key == "rsi"
    assert rsi_indicator.category == "momentum"
    assert rsi_indicator.name == "Relative Strength Index"


def test_rsi_default_params(rsi_indicator):
    """RSI should have default period=14 and source=close."""
    assert rsi_indicator.default_params["period"] == 14
    assert rsi_indicator.default_params["source"] == "close"


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_rsi_calculate_structure(rsi_indicator, sample_candles):
    """calculate() should return a dict with all required keys."""
    result = rsi_indicator.calculate(sample_candles, period=14)
    assert "rsi" in result
    assert "avg_gain" in result
    assert "avg_loss" in result
    assert "current_rsi" in result
    assert "prev_rsi" in result
    assert len(result["rsi"]) == len(sample_candles)


def test_rsi_range(rsi_indicator, sample_candles):
    """All non-None RSI values should be in [0, 100]."""
    result = rsi_indicator.calculate(sample_candles, period=14)
    rsi_values = [v for v in result["rsi"] if v is not None]
    assert len(rsi_values) > 0
    for val in rsi_values:
        assert 0.0 <= val <= 100.0, f"RSI value {val} is out of range"


def test_rsi_warmup_period(rsi_indicator, sample_candles):
    """First 'period' values should be None (warmup)."""
    period = 14
    result = rsi_indicator.calculate(sample_candles, period=period)
    for i in range(period):
        assert result["rsi"][i] is None, f"RSI at index {i} should be None"
    # Value at index 'period' should exist
    assert result["rsi"][period] is not None


def test_rsi_values_vary(rsi_indicator, sample_candles):
    """RSI values should not all be the same (sanity check)."""
    result = rsi_indicator.calculate(sample_candles, period=14)
    rsi_values = [v for v in result["rsi"] if v is not None]
    assert len(set(round(v, 4) for v in rsi_values)) > 1


def test_rsi_current_matches_last(rsi_indicator, sample_candles):
    """current_rsi should equal the last non-None value in the series."""
    result = rsi_indicator.calculate(sample_candles, period=14)
    assert result["current_rsi"] == result["rsi"][-1]


def test_rsi_too_few_candles(rsi_indicator, sample_candles):
    """With fewer candles than period+1, all values should be None."""
    result = rsi_indicator.calculate(sample_candles[:10], period=14)
    assert all(v is None for v in result["rsi"])
    assert result["current_rsi"] is None


def test_rsi_custom_period(rsi_indicator, sample_candles):
    """RSI should work with a custom period."""
    result = rsi_indicator.calculate(sample_candles, period=7)
    rsi_values = [v for v in result["rsi"] if v is not None]
    assert len(rsi_values) > 0
    # Shorter period means more computed values
    result_14 = rsi_indicator.calculate(sample_candles, period=14)
    rsi_14 = [v for v in result_14["rsi"] if v is not None]
    assert len(rsi_values) > len(rsi_14)


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_rsi_update_incremental(rsi_indicator, sample_candles):
    """Incremental update should produce a value close to full recalc."""
    # Full calc on all but last candle
    state = rsi_indicator.calculate(sample_candles[:-1], period=14)
    # Store last close for incremental update
    state["last_close"] = sample_candles[-2].close

    # Update with last candle
    updated = rsi_indicator.update(sample_candles[-1], state, period=14)

    # Full calc including last candle
    full = rsi_indicator.calculate(sample_candles, period=14)

    # Values should be very close
    assert updated["current_rsi"] == pytest.approx(full["current_rsi"], rel=1e-6)


def test_rsi_update_appends(rsi_indicator, sample_candles):
    """update() should append one value to the rsi list."""
    state = rsi_indicator.calculate(sample_candles[:-1], period=14)
    state["last_close"] = sample_candles[-2].close
    original_len = len(state["rsi"])

    rsi_indicator.update(sample_candles[-1], state, period=14)
    assert len(state["rsi"]) == original_len + 1


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_rsi_evaluate_above(rsi_indicator):
    """'above' operator should detect RSI above threshold."""
    state = {"current_rsi": 75.0, "prev_rsi": 72.0}
    assert rsi_indicator.evaluate(state, "above", 70) is True
    assert rsi_indicator.evaluate(state, "above", 80) is False


def test_rsi_evaluate_below(rsi_indicator):
    """'below' operator should detect RSI below threshold."""
    state = {"current_rsi": 25.0, "prev_rsi": 28.0}
    assert rsi_indicator.evaluate(state, "below", 30) is True
    assert rsi_indicator.evaluate(state, "below", 20) is False


def test_rsi_evaluate_cross_up(rsi_indicator):
    """'cross_up' should detect RSI crossing above a value."""
    state = {"current_rsi": 32.0, "prev_rsi": 28.0}
    assert rsi_indicator.evaluate(state, "cross_up", 30) is True
    # Not a cross if both above
    state2 = {"current_rsi": 35.0, "prev_rsi": 32.0}
    assert rsi_indicator.evaluate(state2, "cross_up", 30) is False


def test_rsi_evaluate_cross_down(rsi_indicator):
    """'cross_down' should detect RSI crossing below a value."""
    state = {"current_rsi": 68.0, "prev_rsi": 72.0}
    assert rsi_indicator.evaluate(state, "cross_down", 70) is True
    # Not a cross if both below
    state2 = {"current_rsi": 65.0, "prev_rsi": 68.0}
    assert rsi_indicator.evaluate(state2, "cross_down", 70) is False


def test_rsi_evaluate_rising(rsi_indicator):
    """'rising' should detect increasing RSI."""
    state = {"current_rsi": 55.0, "prev_rsi": 50.0}
    assert rsi_indicator.evaluate(state, "rising") is True
    state["current_rsi"] = 48.0
    assert rsi_indicator.evaluate(state, "rising") is False


def test_rsi_evaluate_falling(rsi_indicator):
    """'falling' should detect decreasing RSI."""
    state = {"current_rsi": 45.0, "prev_rsi": 50.0}
    assert rsi_indicator.evaluate(state, "falling") is True


def test_rsi_evaluate_none_state(rsi_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_rsi": None, "prev_rsi": None}
    assert rsi_indicator.evaluate(state, "above", 50) is False
    assert rsi_indicator.evaluate(state, "cross_up", 30) is False


def test_rsi_evaluate_unknown_operator(rsi_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_rsi": 50.0, "prev_rsi": 48.0}
    with pytest.raises(ValueError, match="Unknown RSI operator"):
        rsi_indicator.evaluate(state, "nonsense", 50)
