"""Tests for the Stochastic RSI indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def stoch_rsi_indicator():
    """Return the registered StochRSI indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("stochastic_rsi")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_stoch_rsi_registered(stoch_rsi_indicator):
    """StochRSI should be registered in the global registry."""
    assert stoch_rsi_indicator.key == "stochastic_rsi"
    assert stoch_rsi_indicator.category == "momentum"
    assert stoch_rsi_indicator.name == "Stochastic RSI"


def test_stoch_rsi_default_params(stoch_rsi_indicator):
    """StochRSI should have standard default params."""
    assert stoch_rsi_indicator.default_params["rsi_period"] == 14
    assert stoch_rsi_indicator.default_params["stoch_period"] == 14
    assert stoch_rsi_indicator.default_params["k_smooth"] == 3
    assert stoch_rsi_indicator.default_params["d_smooth"] == 3


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_stoch_rsi_calculate_structure(stoch_rsi_indicator, sample_candles):
    """calculate() should return all required keys."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    expected_keys = [
        "stoch_rsi", "k", "d", "rsi_values",
        "current_k", "current_d", "prev_k", "prev_d",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    assert len(result["k"]) == len(sample_candles)
    assert len(result["d"]) == len(sample_candles)


def test_stoch_rsi_raw_range(stoch_rsi_indicator, sample_candles):
    """All non-None raw StochRSI values should be in [0, 1]."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    stoch_values = [v for v in result["stoch_rsi"] if v is not None]
    assert len(stoch_values) > 0
    for val in stoch_values:
        assert 0.0 <= val <= 1.0, f"StochRSI raw value {val} is out of [0,1]"


def test_stoch_rsi_k_range(stoch_rsi_indicator, sample_candles):
    """All non-None %K values should be in [0, 1] (with float tolerance)."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    k_values = [v for v in result["k"] if v is not None]
    assert len(k_values) > 0
    eps = 1e-10
    for val in k_values:
        assert -eps <= val <= 1.0 + eps, f"StochRSI %K value {val} is out of [0,1]"


def test_stoch_rsi_d_range(stoch_rsi_indicator, sample_candles):
    """All non-None %D values should be in [0, 1] (with float tolerance)."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    d_values = [v for v in result["d"] if v is not None]
    assert len(d_values) > 0
    eps = 1e-10
    for val in d_values:
        assert -eps <= val <= 1.0 + eps, f"StochRSI %D value {val} is out of [0,1]"


def test_stoch_rsi_has_warmup(stoch_rsi_indicator, sample_candles):
    """Early values should be None due to warmup period."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    # RSI needs rsi_period+1, then Stoch needs stoch_period more
    # So significant warmup expected
    rsi_period = stoch_rsi_indicator.default_params["rsi_period"]
    none_count = sum(1 for v in result["k"] if v is None)
    assert none_count >= rsi_period


def test_stoch_rsi_values_vary(stoch_rsi_indicator, sample_candles):
    """StochRSI values should vary across different candles."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    k_values = [v for v in result["k"] if v is not None]
    assert len(set(round(v, 6) for v in k_values)) > 1


def test_stoch_rsi_rsi_values_exist(stoch_rsi_indicator, sample_candles):
    """Underlying RSI values should be computed correctly."""
    result = stoch_rsi_indicator.calculate(sample_candles)
    rsi_computed = [v for v in result["rsi_values"] if v is not None]
    assert len(rsi_computed) > 0
    for val in rsi_computed:
        assert 0.0 <= val <= 100.0


def test_stoch_rsi_too_few_candles(stoch_rsi_indicator, sample_candles):
    """With very few candles, all values should be None."""
    result = stoch_rsi_indicator.calculate(sample_candles[:10])
    assert all(v is None for v in result["k"])
    assert all(v is None for v in result["d"])


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_stoch_rsi_update_appends(stoch_rsi_indicator, sample_candles):
    """update() should append values to k and d lists."""
    state = stoch_rsi_indicator.calculate(sample_candles[:-1])
    original_len = len(state["k"])

    stoch_rsi_indicator.update(sample_candles[-1], state)

    assert len(state["k"]) == original_len + 1
    assert len(state["d"]) == original_len + 1


def test_stoch_rsi_update_k_range(stoch_rsi_indicator, sample_candles):
    """Updated %K should be in [0, 1] range if not None."""
    state = stoch_rsi_indicator.calculate(sample_candles[:-1])
    stoch_rsi_indicator.update(sample_candles[-1], state)

    new_k = state["current_k"]
    if new_k is not None:
        assert 0.0 <= new_k <= 1.0


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_stoch_rsi_evaluate_overbought(stoch_rsi_indicator):
    """'overbought' should detect %K above threshold (0-1 scale)."""
    state = {"current_k": 0.85, "current_d": 0.82, "prev_k": 0.78, "prev_d": 0.75}
    assert stoch_rsi_indicator.evaluate(state, "overbought") is True  # default 0.8
    assert stoch_rsi_indicator.evaluate(state, "overbought", 0.9) is False


def test_stoch_rsi_evaluate_oversold(stoch_rsi_indicator):
    """'oversold' should detect %K below threshold (0-1 scale)."""
    state = {"current_k": 0.15, "current_d": 0.18, "prev_k": 0.22, "prev_d": 0.25}
    assert stoch_rsi_indicator.evaluate(state, "oversold") is True  # default 0.2
    assert stoch_rsi_indicator.evaluate(state, "oversold", 0.1) is False


def test_stoch_rsi_evaluate_cross_up(stoch_rsi_indicator):
    """'cross_up' should detect %K crossing above %D."""
    state = {"current_k": 0.30, "current_d": 0.25, "prev_k": 0.22, "prev_d": 0.25}
    assert stoch_rsi_indicator.evaluate(state, "cross_up") is True


def test_stoch_rsi_evaluate_cross_up_no_cross(stoch_rsi_indicator):
    """'cross_up' should return False when no crossover occurred."""
    state = {"current_k": 0.30, "current_d": 0.25, "prev_k": 0.28, "prev_d": 0.25}
    assert stoch_rsi_indicator.evaluate(state, "cross_up") is False


def test_stoch_rsi_evaluate_cross_down(stoch_rsi_indicator):
    """'cross_down' should detect %K crossing below %D."""
    state = {"current_k": 0.70, "current_d": 0.75, "prev_k": 0.78, "prev_d": 0.75}
    assert stoch_rsi_indicator.evaluate(state, "cross_down") is True


def test_stoch_rsi_evaluate_none_state(stoch_rsi_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_k": None, "current_d": None, "prev_k": None, "prev_d": None}
    assert stoch_rsi_indicator.evaluate(state, "overbought") is False
    assert stoch_rsi_indicator.evaluate(state, "cross_up") is False


def test_stoch_rsi_evaluate_unknown_operator(stoch_rsi_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_k": 0.5, "current_d": 0.5, "prev_k": 0.48, "prev_d": 0.49}
    with pytest.raises(ValueError, match="Unknown StochasticRSI operator"):
        stoch_rsi_indicator.evaluate(state, "nonsense")
