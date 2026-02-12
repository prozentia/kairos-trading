"""Tests for the TSI (True Strength Index) indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def tsi_indicator():
    """Return the registered TSI indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("tsi")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_tsi_registered(tsi_indicator):
    """TSI should be registered in the global registry."""
    assert tsi_indicator.key == "tsi"
    assert tsi_indicator.category == "momentum"
    assert tsi_indicator.name == "True Strength Index"


def test_tsi_default_params(tsi_indicator):
    """TSI should have standard default params."""
    assert tsi_indicator.default_params["long_period"] == 25
    assert tsi_indicator.default_params["short_period"] == 13
    assert tsi_indicator.default_params["signal_period"] == 7


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_tsi_calculate_structure(tsi_indicator, sample_candles):
    """calculate() should return all required keys."""
    result = tsi_indicator.calculate(sample_candles)
    expected_keys = [
        "tsi", "signal",
        "current_tsi", "current_signal",
        "prev_tsi", "prev_signal",
        "_last_close",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    assert len(result["tsi"]) == len(sample_candles)
    assert len(result["signal"]) == len(sample_candles)


def test_tsi_range(tsi_indicator, sample_candles):
    """TSI values should be in [-100, 100] range."""
    result = tsi_indicator.calculate(sample_candles)
    tsi_values = [v for v in result["tsi"] if v is not None]
    assert len(tsi_values) > 0
    for val in tsi_values:
        assert -100.0 <= val <= 100.0, f"TSI value {val} is out of [-100, 100]"


def test_tsi_signal_range(tsi_indicator, sample_candles):
    """Signal line values should also be in [-100, 100] range."""
    result = tsi_indicator.calculate(sample_candles)
    signal_values = [v for v in result["signal"] if v is not None]
    # Signal might have fewer values due to extra smoothing
    if signal_values:
        for val in signal_values:
            assert -100.0 <= val <= 100.0, f"Signal value {val} is out of [-100, 100]"


def test_tsi_has_warmup(tsi_indicator, sample_candles):
    """TSI should have a significant warmup period due to double smoothing."""
    result = tsi_indicator.calculate(sample_candles)
    none_count = sum(1 for v in result["tsi"] if v is None)
    # long_period(25) + short_period(13) + buffer = significant warmup
    assert none_count >= 25


def test_tsi_values_vary(tsi_indicator, sample_candles):
    """TSI values should vary across different candles."""
    result = tsi_indicator.calculate(sample_candles)
    tsi_values = [v for v in result["tsi"] if v is not None]
    assert len(set(round(v, 4) for v in tsi_values)) > 1


def test_tsi_current_matches_last(tsi_indicator, sample_candles):
    """current_tsi should equal the last non-None tsi value."""
    result = tsi_indicator.calculate(sample_candles)
    last_tsi = result["tsi"][-1]
    assert result["current_tsi"] == last_tsi


def test_tsi_too_few_candles(tsi_indicator, sample_candles):
    """With very few candles, all TSI values should be None."""
    result = tsi_indicator.calculate(sample_candles[:5])
    assert all(v is None for v in result["tsi"])


def test_tsi_signal_after_tsi(tsi_indicator, sample_candles):
    """Signal line should start after TSI (needs signal_period more data)."""
    result = tsi_indicator.calculate(sample_candles)
    tsi_first_idx = None
    signal_first_idx = None
    for i, v in enumerate(result["tsi"]):
        if v is not None and tsi_first_idx is None:
            tsi_first_idx = i
    for i, v in enumerate(result["signal"]):
        if v is not None and signal_first_idx is None:
            signal_first_idx = i
    if tsi_first_idx is not None and signal_first_idx is not None:
        assert signal_first_idx >= tsi_first_idx


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_tsi_update_appends(tsi_indicator, sample_candles):
    """update() should append values to tsi and signal lists."""
    state = tsi_indicator.calculate(sample_candles[:-1])
    original_len = len(state["tsi"])

    tsi_indicator.update(sample_candles[-1], state)

    assert len(state["tsi"]) == original_len + 1
    assert len(state["signal"]) == original_len + 1


def test_tsi_update_incremental(tsi_indicator, sample_candles):
    """Incremental update should produce a value close to full recalc."""
    state = tsi_indicator.calculate(sample_candles[:-1])
    updated = tsi_indicator.update(sample_candles[-1], state)

    full = tsi_indicator.calculate(sample_candles)

    if full["current_tsi"] is not None and updated["current_tsi"] is not None:
        assert updated["current_tsi"] == pytest.approx(
            full["current_tsi"], rel=1e-4
        )


def test_tsi_update_range(tsi_indicator, sample_candles):
    """Updated TSI should be in [-100, 100] range if not None."""
    state = tsi_indicator.calculate(sample_candles[:-1])
    tsi_indicator.update(sample_candles[-1], state)

    new_tsi = state["current_tsi"]
    if new_tsi is not None:
        assert -100.0 <= new_tsi <= 100.0


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_tsi_evaluate_above_zero(tsi_indicator):
    """'above_zero' should detect TSI > 0."""
    state = {"current_tsi": 15.0, "current_signal": 10.0,
             "prev_tsi": 12.0, "prev_signal": 11.0}
    assert tsi_indicator.evaluate(state, "above_zero") is True
    state["current_tsi"] = -5.0
    assert tsi_indicator.evaluate(state, "above_zero") is False


def test_tsi_evaluate_below_zero(tsi_indicator):
    """'below_zero' should detect TSI < 0."""
    state = {"current_tsi": -15.0, "current_signal": -10.0,
             "prev_tsi": -12.0, "prev_signal": -11.0}
    assert tsi_indicator.evaluate(state, "below_zero") is True
    state["current_tsi"] = 5.0
    assert tsi_indicator.evaluate(state, "below_zero") is False


def test_tsi_evaluate_above(tsi_indicator):
    """'above' should detect TSI > value."""
    state = {"current_tsi": 20.0, "current_signal": 15.0,
             "prev_tsi": 18.0, "prev_signal": 16.0}
    assert tsi_indicator.evaluate(state, "above", 10) is True
    assert tsi_indicator.evaluate(state, "above", 25) is False


def test_tsi_evaluate_below(tsi_indicator):
    """'below' should detect TSI < value."""
    state = {"current_tsi": -20.0, "current_signal": -15.0,
             "prev_tsi": -18.0, "prev_signal": -16.0}
    assert tsi_indicator.evaluate(state, "below", -10) is True
    assert tsi_indicator.evaluate(state, "below", -25) is False


def test_tsi_evaluate_cross_up(tsi_indicator):
    """'cross_up' should detect TSI crossing above signal line."""
    state = {
        "current_tsi": 12.0, "current_signal": 10.0,
        "prev_tsi": 8.0, "prev_signal": 10.0,
    }
    assert tsi_indicator.evaluate(state, "cross_up") is True


def test_tsi_evaluate_cross_up_no_cross(tsi_indicator):
    """'cross_up' should return False when no crossover."""
    state = {
        "current_tsi": 12.0, "current_signal": 10.0,
        "prev_tsi": 11.0, "prev_signal": 10.0,
    }
    assert tsi_indicator.evaluate(state, "cross_up") is False


def test_tsi_evaluate_cross_down(tsi_indicator):
    """'cross_down' should detect TSI crossing below signal line."""
    state = {
        "current_tsi": 8.0, "current_signal": 10.0,
        "prev_tsi": 12.0, "prev_signal": 10.0,
    }
    assert tsi_indicator.evaluate(state, "cross_down") is True


def test_tsi_evaluate_rising(tsi_indicator):
    """'rising' should detect increasing TSI."""
    state = {"current_tsi": 15.0, "prev_tsi": 10.0,
             "current_signal": 12.0, "prev_signal": 11.0}
    assert tsi_indicator.evaluate(state, "rising") is True
    state["current_tsi"] = 8.0
    assert tsi_indicator.evaluate(state, "rising") is False


def test_tsi_evaluate_falling(tsi_indicator):
    """'falling' should detect decreasing TSI."""
    state = {"current_tsi": 8.0, "prev_tsi": 15.0,
             "current_signal": 12.0, "prev_signal": 13.0}
    assert tsi_indicator.evaluate(state, "falling") is True


def test_tsi_evaluate_none_state(tsi_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_tsi": None, "current_signal": None,
             "prev_tsi": None, "prev_signal": None}
    assert tsi_indicator.evaluate(state, "above_zero") is False
    assert tsi_indicator.evaluate(state, "cross_up") is False
    assert tsi_indicator.evaluate(state, "rising") is False


def test_tsi_evaluate_unknown_operator(tsi_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_tsi": 15.0, "current_signal": 10.0,
             "prev_tsi": 12.0, "prev_signal": 11.0}
    with pytest.raises(ValueError, match="Unknown TSI operator"):
        tsi_indicator.evaluate(state, "nonsense")
