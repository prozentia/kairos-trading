"""Tests for the Stochastic Oscillator indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def stoch_indicator():
    """Return the registered Stochastic indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("stochastic")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_stochastic_registered(stoch_indicator):
    """Stochastic should be registered in the global registry."""
    assert stoch_indicator.key == "stochastic"
    assert stoch_indicator.category == "momentum"
    assert stoch_indicator.name == "Stochastic Oscillator"


def test_stochastic_default_params(stoch_indicator):
    """Stochastic should have standard default params."""
    assert stoch_indicator.default_params["k_period"] == 14
    assert stoch_indicator.default_params["d_period"] == 3
    assert stoch_indicator.default_params["smooth"] == 3


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_stochastic_calculate_structure(stoch_indicator, sample_candles):
    """calculate() should return all required keys."""
    result = stoch_indicator.calculate(sample_candles)
    expected_keys = ["k", "d", "raw_k", "current_k", "current_d", "prev_k", "prev_d"]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    assert len(result["k"]) == len(sample_candles)
    assert len(result["d"]) == len(sample_candles)


def test_stochastic_k_range(stoch_indicator, sample_candles):
    """All non-None %K values should be in [0, 100]."""
    result = stoch_indicator.calculate(sample_candles)
    k_values = [v for v in result["k"] if v is not None]
    assert len(k_values) > 0
    for val in k_values:
        assert 0.0 <= val <= 100.0, f"%K value {val} is out of range"


def test_stochastic_d_range(stoch_indicator, sample_candles):
    """All non-None %D values should be in [0, 100]."""
    result = stoch_indicator.calculate(sample_candles)
    d_values = [v for v in result["d"] if v is not None]
    assert len(d_values) > 0
    for val in d_values:
        assert 0.0 <= val <= 100.0, f"%D value {val} is out of range"


def test_stochastic_raw_k_range(stoch_indicator, sample_candles):
    """All non-None raw %K values should be in [0, 100]."""
    result = stoch_indicator.calculate(sample_candles)
    raw_k = [v for v in result["raw_k"] if v is not None]
    assert len(raw_k) > 0
    for val in raw_k:
        assert 0.0 <= val <= 100.0, f"Raw %K value {val} is out of range"


def test_stochastic_warmup_period(stoch_indicator, sample_candles):
    """First k_period - 1 values should be None."""
    result = stoch_indicator.calculate(sample_candles)
    k_period = stoch_indicator.default_params["k_period"]
    for i in range(k_period - 1):
        assert result["raw_k"][i] is None


def test_stochastic_values_vary(stoch_indicator, sample_candles):
    """Stochastic values should vary across different candles."""
    result = stoch_indicator.calculate(sample_candles)
    k_values = [v for v in result["k"] if v is not None]
    assert len(set(round(v, 4) for v in k_values)) > 1


def test_stochastic_current_matches_last(stoch_indicator, sample_candles):
    """current_k should equal the last non-None K value."""
    result = stoch_indicator.calculate(sample_candles)
    assert result["current_k"] == result["k"][-1]


def test_stochastic_too_few_candles(stoch_indicator, sample_candles):
    """With fewer candles than k_period, all raw_k should be None."""
    result = stoch_indicator.calculate(sample_candles[:10])
    assert all(v is None for v in result["raw_k"])


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_stochastic_update_appends(stoch_indicator, sample_candles):
    """update() should append values to k and d lists."""
    state = stoch_indicator.calculate(sample_candles[:-1])
    original_len = len(state["k"])

    stoch_indicator.update(sample_candles[-1], state)

    assert len(state["k"]) == original_len + 1
    assert len(state["d"]) == original_len + 1


def test_stochastic_update_k_range(stoch_indicator, sample_candles):
    """Updated %K should be in [0, 100] range."""
    state = stoch_indicator.calculate(sample_candles[:-1])
    stoch_indicator.update(sample_candles[-1], state)

    new_k = state["current_k"]
    if new_k is not None:
        assert 0.0 <= new_k <= 100.0


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_stochastic_evaluate_overbought(stoch_indicator):
    """'overbought' should detect %K above threshold."""
    state = {"current_k": 85.0, "current_d": 82.0, "prev_k": 78.0, "prev_d": 75.0}
    assert stoch_indicator.evaluate(state, "overbought") is True  # default 80
    assert stoch_indicator.evaluate(state, "overbought", 90) is False


def test_stochastic_evaluate_oversold(stoch_indicator):
    """'oversold' should detect %K below threshold."""
    state = {"current_k": 15.0, "current_d": 18.0, "prev_k": 22.0, "prev_d": 25.0}
    assert stoch_indicator.evaluate(state, "oversold") is True  # default 20
    assert stoch_indicator.evaluate(state, "oversold", 10) is False


def test_stochastic_evaluate_cross_up(stoch_indicator):
    """'cross_up' should detect %K crossing above %D."""
    state = {"current_k": 30.0, "current_d": 25.0, "prev_k": 22.0, "prev_d": 25.0}
    assert stoch_indicator.evaluate(state, "cross_up") is True


def test_stochastic_evaluate_cross_up_no_cross(stoch_indicator):
    """'cross_up' should return False when no crossover occurred."""
    state = {"current_k": 30.0, "current_d": 25.0, "prev_k": 28.0, "prev_d": 25.0}
    assert stoch_indicator.evaluate(state, "cross_up") is False


def test_stochastic_evaluate_cross_down(stoch_indicator):
    """'cross_down' should detect %K crossing below %D."""
    state = {"current_k": 70.0, "current_d": 75.0, "prev_k": 78.0, "prev_d": 75.0}
    assert stoch_indicator.evaluate(state, "cross_down") is True


def test_stochastic_evaluate_cross_down_no_cross(stoch_indicator):
    """'cross_down' should return False when no crossover occurred."""
    state = {"current_k": 70.0, "current_d": 75.0, "prev_k": 72.0, "prev_d": 75.0}
    assert stoch_indicator.evaluate(state, "cross_down") is False


def test_stochastic_evaluate_none_state(stoch_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_k": None, "current_d": None, "prev_k": None, "prev_d": None}
    assert stoch_indicator.evaluate(state, "overbought") is False
    assert stoch_indicator.evaluate(state, "cross_up") is False


def test_stochastic_evaluate_unknown_operator(stoch_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_k": 50.0, "current_d": 50.0, "prev_k": 48.0, "prev_d": 49.0}
    with pytest.raises(ValueError, match="Unknown Stochastic operator"):
        stoch_indicator.evaluate(state, "nonsense")
