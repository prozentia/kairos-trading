"""Tests for the MACD (Moving Average Convergence Divergence) indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def macd_indicator():
    """Return the registered MACD indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("macd")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_macd_registered(macd_indicator):
    """MACD should be registered in the global registry."""
    assert macd_indicator.key == "macd"
    assert macd_indicator.category == "momentum"
    assert macd_indicator.name == "MACD"


def test_macd_default_params(macd_indicator):
    """MACD should have standard default params."""
    assert macd_indicator.default_params["fast_period"] == 12
    assert macd_indicator.default_params["slow_period"] == 26
    assert macd_indicator.default_params["signal_period"] == 9


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_macd_calculate_structure(macd_indicator, sample_candles):
    """calculate() should return all required keys."""
    result = macd_indicator.calculate(sample_candles)
    expected_keys = [
        "macd_line", "signal_line", "histogram",
        "fast_ema", "slow_ema",
        "current_macd", "current_signal", "current_histogram",
        "prev_macd", "prev_signal", "prev_histogram",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    assert len(result["macd_line"]) == len(sample_candles)
    assert len(result["signal_line"]) == len(sample_candles)
    assert len(result["histogram"]) == len(sample_candles)


def test_macd_warmup_period(macd_indicator, sample_candles):
    """MACD line should have None values during warmup."""
    result = macd_indicator.calculate(sample_candles)
    slow = macd_indicator.default_params["slow_period"]
    # First (slow_period - 1) values should be None
    for i in range(slow - 1):
        assert result["macd_line"][i] is None


def test_macd_line_is_difference(macd_indicator, sample_candles):
    """MACD line should equal fast_ema - slow_ema where both exist."""
    result = macd_indicator.calculate(sample_candles)
    for i in range(len(sample_candles)):
        f = result["fast_ema"][i]
        s = result["slow_ema"][i]
        m = result["macd_line"][i]
        if f is not None and s is not None:
            assert m == pytest.approx(f - s, abs=1e-8)
        elif m is not None:
            # Should only be non-None when both EMAs exist
            assert False, f"MACD at {i} is non-None but an EMA is None"


def test_macd_histogram_is_difference(macd_indicator, sample_candles):
    """Histogram should equal MACD line - signal line where both exist."""
    result = macd_indicator.calculate(sample_candles)
    for i in range(len(sample_candles)):
        m = result["macd_line"][i]
        s = result["signal_line"][i]
        h = result["histogram"][i]
        if m is not None and s is not None:
            assert h == pytest.approx(m - s, abs=1e-8)


def test_macd_values_exist(macd_indicator, sample_candles):
    """With 500 candles, MACD should have many computed values."""
    result = macd_indicator.calculate(sample_candles)
    macd_computed = [v for v in result["macd_line"] if v is not None]
    signal_computed = [v for v in result["signal_line"] if v is not None]
    hist_computed = [v for v in result["histogram"] if v is not None]
    assert len(macd_computed) > 400
    assert len(signal_computed) > 400
    assert len(hist_computed) > 400


def test_macd_too_few_candles(macd_indicator, sample_candles):
    """With fewer candles than slow_period, all MACD values should be None."""
    result = macd_indicator.calculate(sample_candles[:20])
    assert all(v is None for v in result["macd_line"])


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_macd_update_incremental(macd_indicator, sample_candles):
    """Incremental update should match full recalculation."""
    state = macd_indicator.calculate(sample_candles[:-1])
    updated = macd_indicator.update(sample_candles[-1], state)

    full = macd_indicator.calculate(sample_candles)

    assert updated["current_macd"] == pytest.approx(full["current_macd"], rel=1e-6)
    if full["current_signal"] is not None:
        assert updated["current_signal"] == pytest.approx(
            full["current_signal"], rel=1e-6
        )


def test_macd_update_appends(macd_indicator, sample_candles):
    """update() should append one value to each series."""
    state = macd_indicator.calculate(sample_candles[:-1])
    original_len = len(state["macd_line"])

    macd_indicator.update(sample_candles[-1], state)

    assert len(state["macd_line"]) == original_len + 1
    assert len(state["signal_line"]) == original_len + 1
    assert len(state["histogram"]) == original_len + 1


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_macd_evaluate_cross_up(macd_indicator):
    """'cross_up' should detect bullish MACD/signal crossover."""
    state = {
        "current_macd": 0.5,
        "current_signal": 0.3,
        "prev_macd": 0.2,
        "prev_signal": 0.3,
        "current_histogram": 0.2,
        "prev_histogram": -0.1,
    }
    assert macd_indicator.evaluate(state, "cross_up") is True


def test_macd_evaluate_cross_down(macd_indicator):
    """'cross_down' should detect bearish MACD/signal crossover."""
    state = {
        "current_macd": 0.1,
        "current_signal": 0.3,
        "prev_macd": 0.4,
        "prev_signal": 0.3,
        "current_histogram": -0.2,
        "prev_histogram": 0.1,
    }
    assert macd_indicator.evaluate(state, "cross_down") is True


def test_macd_evaluate_above_zero(macd_indicator):
    """'above_zero' should check if MACD line is positive."""
    state = {"current_macd": 5.0, "current_signal": 3.0,
             "current_histogram": 2.0, "prev_macd": 4.0,
             "prev_signal": 3.0, "prev_histogram": 1.0}
    assert macd_indicator.evaluate(state, "above_zero") is True
    state["current_macd"] = -1.0
    assert macd_indicator.evaluate(state, "above_zero") is False


def test_macd_evaluate_below_zero(macd_indicator):
    """'below_zero' should check if MACD line is negative."""
    state = {"current_macd": -5.0, "current_signal": -3.0,
             "current_histogram": -2.0, "prev_macd": -4.0,
             "prev_signal": -3.0, "prev_histogram": -1.0}
    assert macd_indicator.evaluate(state, "below_zero") is True


def test_macd_evaluate_histogram_positive(macd_indicator):
    """'histogram_positive' should check histogram > 0."""
    state = {"current_macd": 5.0, "current_signal": 3.0,
             "current_histogram": 2.0, "prev_histogram": 1.0}
    assert macd_indicator.evaluate(state, "histogram_positive") is True
    state["current_histogram"] = -1.0
    assert macd_indicator.evaluate(state, "histogram_positive") is False


def test_macd_evaluate_histogram_negative(macd_indicator):
    """'histogram_negative' should check histogram < 0."""
    state = {"current_macd": 1.0, "current_signal": 3.0,
             "current_histogram": -2.0, "prev_histogram": -1.0}
    assert macd_indicator.evaluate(state, "histogram_negative") is True


def test_macd_evaluate_histogram_rising(macd_indicator):
    """'histogram_rising' should detect increasing histogram."""
    state = {"current_histogram": 2.0, "prev_histogram": 1.0,
             "current_macd": 5.0, "current_signal": 3.0}
    assert macd_indicator.evaluate(state, "histogram_rising") is True
    state["current_histogram"] = 0.5
    assert macd_indicator.evaluate(state, "histogram_rising") is False


def test_macd_evaluate_histogram_falling(macd_indicator):
    """'histogram_falling' should detect decreasing histogram."""
    state = {"current_histogram": 0.5, "prev_histogram": 1.5,
             "current_macd": 5.0, "current_signal": 4.5}
    assert macd_indicator.evaluate(state, "histogram_falling") is True


def test_macd_evaluate_none_state(macd_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_macd": None, "current_signal": None,
             "current_histogram": None, "prev_macd": None,
             "prev_signal": None, "prev_histogram": None}
    assert macd_indicator.evaluate(state, "cross_up") is False
    assert macd_indicator.evaluate(state, "above_zero") is False
    assert macd_indicator.evaluate(state, "histogram_rising") is False


def test_macd_evaluate_unknown_operator(macd_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_macd": 5.0, "current_signal": 3.0,
             "current_histogram": 2.0, "prev_histogram": 1.0}
    with pytest.raises(ValueError, match="Unknown MACD operator"):
        macd_indicator.evaluate(state, "nonsense")
