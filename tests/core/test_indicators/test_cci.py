"""Tests for the CCI (Commodity Channel Index) indicator.

Validates calculate(), update(), and evaluate() methods with
mathematical correctness checks, edge cases, and signal detection.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def cci_indicator():
    """Return the registered CCI indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("cci")


# ------------------------------------------------------------------
# Registration & metadata
# ------------------------------------------------------------------

def test_cci_registered(cci_indicator):
    """CCI should be registered in the global registry."""
    assert cci_indicator.key == "cci"
    assert cci_indicator.category == "momentum"
    assert cci_indicator.name == "Commodity Channel Index"


def test_cci_default_params(cci_indicator):
    """CCI should have standard default params."""
    assert cci_indicator.default_params["period"] == 20
    assert cci_indicator.default_params["constant"] == 0.015


# ------------------------------------------------------------------
# calculate() — full computation
# ------------------------------------------------------------------

def test_cci_calculate_structure(cci_indicator, sample_candles):
    """calculate() should return all required keys."""
    result = cci_indicator.calculate(sample_candles)
    expected_keys = ["cci", "current_cci", "prev_cci", "tp_buffer"]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    assert len(result["cci"]) == len(sample_candles)


def test_cci_warmup_period(cci_indicator, sample_candles):
    """First (period - 1) CCI values should be None."""
    period = 20
    result = cci_indicator.calculate(sample_candles, period=period)
    for i in range(period - 1):
        assert result["cci"][i] is None
    # Value at index period-1 should exist
    assert result["cci"][period - 1] is not None


def test_cci_values_exist(cci_indicator, sample_candles):
    """With 500 candles, CCI should have many computed values."""
    result = cci_indicator.calculate(sample_candles)
    computed = [v for v in result["cci"] if v is not None]
    assert len(computed) > 400


def test_cci_values_vary(cci_indicator, sample_candles):
    """CCI values should vary across different candles."""
    result = cci_indicator.calculate(sample_candles)
    computed = [v for v in result["cci"] if v is not None]
    assert len(set(round(v, 4) for v in computed)) > 1


def test_cci_typical_range(cci_indicator, sample_candles):
    """CCI typically oscillates; values should not be extreme."""
    result = cci_indicator.calculate(sample_candles)
    computed = [v for v in result["cci"] if v is not None]
    # At least some values should be between -200 and 200
    normal_range = [v for v in computed if -200 <= v <= 200]
    assert len(normal_range) > len(computed) * 0.5


def test_cci_current_matches_last(cci_indicator, sample_candles):
    """current_cci should equal the last value in the series."""
    result = cci_indicator.calculate(sample_candles)
    assert result["current_cci"] == result["cci"][-1]


def test_cci_too_few_candles(cci_indicator, sample_candles):
    """With fewer candles than period, all CCI values should be None."""
    result = cci_indicator.calculate(sample_candles[:15])
    assert all(v is None for v in result["cci"])
    assert result["current_cci"] is None


def test_cci_manual_calculation(cci_indicator):
    """Verify CCI math with a known dataset."""
    from datetime import datetime, timezone
    # Create 3 simple candles; period = 3
    candles = [
        Candle(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
               open=10, high=15, low=5, close=12, volume=100,
               pair="TEST/USD", timeframe="1m"),
        Candle(timestamp=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
               open=12, high=18, low=8, close=14, volume=100,
               pair="TEST/USD", timeframe="1m"),
        Candle(timestamp=datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc),
               open=14, high=20, low=10, close=16, volume=100,
               pair="TEST/USD", timeframe="1m"),
    ]
    result = cci_indicator.calculate(candles, period=3, constant=0.015)

    # TP: (15+5+12)/3=10.667, (18+8+14)/3=13.333, (20+10+16)/3=15.333
    # SMA(TP,3) = (10.667+13.333+15.333)/3 = 13.111
    # Mean Dev = (|10.667-13.111|+|13.333-13.111|+|15.333-13.111|)/3
    #          = (2.444+0.222+2.222)/3 = 1.629
    # CCI = (15.333 - 13.111) / (0.015 * 1.629) = 2.222 / 0.02444 = 90.9
    cci_val = result["cci"][2]
    assert cci_val is not None
    assert 85.0 < cci_val < 100.0  # Approximate check


# ------------------------------------------------------------------
# update() — incremental
# ------------------------------------------------------------------

def test_cci_update_incremental(cci_indicator, sample_candles):
    """Incremental update should match full recalculation."""
    state = cci_indicator.calculate(sample_candles[:-1])
    updated = cci_indicator.update(sample_candles[-1], state)

    full = cci_indicator.calculate(sample_candles)

    if full["current_cci"] is not None:
        assert updated["current_cci"] == pytest.approx(full["current_cci"], rel=1e-6)


def test_cci_update_appends(cci_indicator, sample_candles):
    """update() should append one value to the cci list."""
    state = cci_indicator.calculate(sample_candles[:-1])
    original_len = len(state["cci"])

    cci_indicator.update(sample_candles[-1], state)
    assert len(state["cci"]) == original_len + 1


def test_cci_update_tp_buffer_size(cci_indicator, sample_candles):
    """tp_buffer should not grow beyond period."""
    state = cci_indicator.calculate(sample_candles[:-5])
    period = 20
    for c in sample_candles[-5:]:
        cci_indicator.update(c, state, period=period)
    assert len(state["tp_buffer"]) == period


# ------------------------------------------------------------------
# evaluate() — signal detection
# ------------------------------------------------------------------

def test_cci_evaluate_above(cci_indicator):
    """'above' should detect CCI above a value."""
    state = {"current_cci": 150.0, "prev_cci": 110.0}
    assert cci_indicator.evaluate(state, "above", 100) is True
    assert cci_indicator.evaluate(state, "above", 200) is False


def test_cci_evaluate_below(cci_indicator):
    """'below' should detect CCI below a value."""
    state = {"current_cci": -150.0, "prev_cci": -110.0}
    assert cci_indicator.evaluate(state, "below", -100) is True
    assert cci_indicator.evaluate(state, "below", -200) is False


def test_cci_evaluate_overbought(cci_indicator):
    """'overbought' should detect CCI > +100 by default."""
    state = {"current_cci": 120.0, "prev_cci": 95.0}
    assert cci_indicator.evaluate(state, "overbought") is True
    state["current_cci"] = 80.0
    assert cci_indicator.evaluate(state, "overbought") is False


def test_cci_evaluate_oversold(cci_indicator):
    """'oversold' should detect CCI < -100 by default."""
    state = {"current_cci": -120.0, "prev_cci": -95.0}
    assert cci_indicator.evaluate(state, "oversold") is True
    state["current_cci"] = -80.0
    assert cci_indicator.evaluate(state, "oversold") is False


def test_cci_evaluate_cross_up(cci_indicator):
    """'cross_up' should detect CCI crossing above a value."""
    state = {"current_cci": 5.0, "prev_cci": -5.0}
    assert cci_indicator.evaluate(state, "cross_up", 0) is True
    # Not a cross if prev was already above
    state2 = {"current_cci": 10.0, "prev_cci": 5.0}
    assert cci_indicator.evaluate(state2, "cross_up", 0) is False


def test_cci_evaluate_cross_down(cci_indicator):
    """'cross_down' should detect CCI crossing below a value."""
    state = {"current_cci": -5.0, "prev_cci": 5.0}
    assert cci_indicator.evaluate(state, "cross_down", 0) is True


def test_cci_evaluate_none_state(cci_indicator):
    """evaluate should return False when state values are None."""
    state = {"current_cci": None, "prev_cci": None}
    assert cci_indicator.evaluate(state, "above", 100) is False
    assert cci_indicator.evaluate(state, "cross_up", 0) is False


def test_cci_evaluate_unknown_operator(cci_indicator):
    """Unknown operator should raise ValueError."""
    state = {"current_cci": 50.0, "prev_cci": 48.0}
    with pytest.raises(ValueError, match="Unknown CCI operator"):
        cci_indicator.evaluate(state, "nonsense")
