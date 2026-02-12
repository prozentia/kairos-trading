"""Tests for the ROC (Rate of Change) indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timezone


@pytest.fixture
def roc_indicator():
    """Return the registered ROC indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("roc")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_roc_registered(roc_indicator):
    """ROC should be registered in the global registry."""
    assert roc_indicator.key == "roc"
    assert roc_indicator.category == "momentum"
    assert roc_indicator.name == "Rate of Change"


def test_roc_default_params(roc_indicator):
    """ROC should have standard default params."""
    assert roc_indicator.default_params["period"] == 12
    assert roc_indicator.default_params["source"] == "close"


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_roc_calculate_structure(roc_indicator, sample_candles):
    """calculate() should return all required keys."""
    result = roc_indicator.calculate(sample_candles)
    expected_keys = ["roc", "current_roc", "prev_roc", "price_buffer"]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    assert len(result["roc"]) == len(sample_candles)


def test_roc_warmup_period(roc_indicator, sample_candles):
    """First 'period' values should be None."""
    period = 12
    result = roc_indicator.calculate(sample_candles, period=period)
    for i in range(period):
        assert result["roc"][i] is None
    # Value at index 'period' should exist
    assert result["roc"][period] is not None


def test_roc_values_exist(roc_indicator, sample_candles):
    """With 500 candles, ROC should have many computed values."""
    result = roc_indicator.calculate(sample_candles)
    computed = [v for v in result["roc"] if v is not None]
    assert len(computed) > 450


def test_roc_values_are_percentages(roc_indicator, sample_candles):
    """ROC values should be percentages (small for BTC with small moves)."""
    result = roc_indicator.calculate(sample_candles)
    computed = [v for v in result["roc"] if v is not None]
    # With random walk of -0.3% to +0.3% per candle, 12-period ROC
    # should be relatively small (say within -10% to +10%)
    for val in computed:
        assert -20.0 < val < 20.0, f"ROC value {val} seems unreasonable"


def test_roc_manual_calculation(roc_indicator):
    """Verify ROC math with a known dataset."""
    candles = [
        Candle(timestamp=datetime(2026, 1, 1, 0, i, tzinfo=timezone.utc),
               open=100, high=105, low=95, close=100 + i * 5,
               volume=100, pair="TEST/USD", timeframe="1m")
        for i in range(5)
    ]
    # Closes: 100, 105, 110, 115, 120
    result = roc_indicator.calculate(candles, period=2)
    # ROC at index 2: (110 - 100) / 100 * 100 = 10%
    assert result["roc"][2] == pytest.approx(10.0, rel=1e-6)
    # ROC at index 3: (115 - 105) / 105 * 100 = 9.524%
    assert result["roc"][3] == pytest.approx(100 * (115 - 105) / 105, rel=1e-6)
    # ROC at index 4: (120 - 110) / 110 * 100 = 9.091%
    assert result["roc"][4] == pytest.approx(100 * (120 - 110) / 110, rel=1e-6)


def test_roc_current_matches_last(roc_indicator, sample_candles):
    """current_roc should equal the last value in the series."""
    result = roc_indicator.calculate(sample_candles)
    assert result["current_roc"] == result["roc"][-1]


def test_roc_too_few_candles(roc_indicator, sample_candles):
    """With fewer candles than period, all ROC values should be None."""
    result = roc_indicator.calculate(sample_candles[:10], period=12)
    assert all(v is None for v in result["roc"])


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_roc_update_incremental(roc_indicator, sample_candles):
    """Incremental update should match full recalculation."""
    state = roc_indicator.calculate(sample_candles[:-1])
    updated = roc_indicator.update(sample_candles[-1], state)

    full = roc_indicator.calculate(sample_candles)

    assert updated["current_roc"] == pytest.approx(full["current_roc"], rel=1e-6)


def test_roc_update_appends(roc_indicator, sample_candles):
    """update() should append one value to the roc list."""
    state = roc_indicator.calculate(sample_candles[:-1])
    original_len = len(state["roc"])

    roc_indicator.update(sample_candles[-1], state)
    assert len(state["roc"]) == original_len + 1


def test_roc_update_buffer_bounded(roc_indicator, sample_candles):
    """price_buffer should not grow beyond period + 1."""
    period = 12
    state = roc_indicator.calculate(sample_candles[:-5], period=period)
    for c in sample_candles[-5:]:
        roc_indicator.update(c, state, period=period)
    assert len(state["price_buffer"]) == period + 1


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_roc_evaluate_above(roc_indicator):
    """'above' should detect ROC above a value."""
    state = {"current_roc": 5.0, "prev_roc": 3.0}
    assert roc_indicator.evaluate(state, "above", 2) is True
    assert roc_indicator.evaluate(state, "above", 10) is False


def test_roc_evaluate_below(roc_indicator):
    """'below' should detect ROC below a value."""
    state = {"current_roc": -5.0, "prev_roc": -3.0}
    assert roc_indicator.evaluate(state, "below", -2) is True
    assert roc_indicator.evaluate(state, "below", -10) is False


def test_roc_evaluate_positive(roc_indicator):
    """'positive' should detect ROC > 0."""
    state = {"current_roc": 1.5, "prev_roc": 0.5}
    assert roc_indicator.evaluate(state, "positive") is True
    state["current_roc"] = -0.5
    assert roc_indicator.evaluate(state, "positive") is False


def test_roc_evaluate_negative(roc_indicator):
    """'negative' should detect ROC < 0."""
    state = {"current_roc": -1.5, "prev_roc": -0.5}
    assert roc_indicator.evaluate(state, "negative") is True
    state["current_roc"] = 0.5
    assert roc_indicator.evaluate(state, "negative") is False


def test_roc_evaluate_rising(roc_indicator):
    """'rising' should detect increasing ROC."""
    state = {"current_roc": 5.0, "prev_roc": 3.0}
    assert roc_indicator.evaluate(state, "rising") is True
    state["current_roc"] = 2.0
    assert roc_indicator.evaluate(state, "rising") is False


def test_roc_evaluate_falling(roc_indicator):
    """'falling' should detect decreasing ROC."""
    state = {"current_roc": 2.0, "prev_roc": 5.0}
    assert roc_indicator.evaluate(state, "falling") is True


def test_roc_evaluate_cross_up(roc_indicator):
    """'cross_up' should detect ROC crossing above a value."""
    state = {"current_roc": 1.0, "prev_roc": -1.0}
    assert roc_indicator.evaluate(state, "cross_up", 0) is True
    # Not a cross if already above
    state2 = {"current_roc": 2.0, "prev_roc": 1.0}
    assert roc_indicator.evaluate(state2, "cross_up", 0) is False


def test_roc_evaluate_cross_down(roc_indicator):
    """'cross_down' should detect ROC crossing below a value."""
    state = {"current_roc": -1.0, "prev_roc": 1.0}
    assert roc_indicator.evaluate(state, "cross_down", 0) is True


def test_roc_evaluate_none_state(roc_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_roc": None, "prev_roc": None}
    assert roc_indicator.evaluate(state, "above", 0) is False
    assert roc_indicator.evaluate(state, "positive") is False
    assert roc_indicator.evaluate(state, "cross_up", 0) is False


def test_roc_evaluate_unknown_operator(roc_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_roc": 5.0, "prev_roc": 3.0}
    with pytest.raises(ValueError, match="Unknown ROC operator"):
        roc_indicator.evaluate(state, "nonsense")
