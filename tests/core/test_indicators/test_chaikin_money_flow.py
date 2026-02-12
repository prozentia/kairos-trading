"""Tests for the Chaikin Money Flow (CMF) indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timedelta, timezone


@pytest.fixture
def cmf_indicator():
    """Return the registered CMF indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("chaikin_money_flow")


def test_cmf_registered(cmf_indicator):
    """CMF should be registered in the global registry."""
    assert cmf_indicator.key == "chaikin_money_flow"
    assert cmf_indicator.category == "volume"
    assert cmf_indicator.name == "Chaikin Money Flow"


def test_cmf_default_params(cmf_indicator):
    """CMF should have default period=20."""
    assert cmf_indicator.default_params["period"] == 20


def test_cmf_calculate_returns_keys(cmf_indicator, sample_candles):
    """Calculate should return cmf, mfv, volumes."""
    result = cmf_indicator.calculate(sample_candles)

    assert "cmf" in result
    assert "mfv" in result
    assert "volumes" in result
    assert len(result["cmf"]) == len(sample_candles)


def test_cmf_warmup_period(cmf_indicator, sample_candles):
    """CMF values should be None during warmup."""
    result = cmf_indicator.calculate(sample_candles, period=20)

    for i in range(19):
        assert result["cmf"][i] is None

    assert result["cmf"][19] is not None


def test_cmf_range(cmf_indicator, sample_candles):
    """CMF should be between -1 and 1."""
    result = cmf_indicator.calculate(sample_candles)

    for val in result["cmf"]:
        if val is not None:
            assert -1.0 <= val <= 1.0, f"CMF value {val} out of range"


def test_cmf_manual_calculation(cmf_indicator):
    """Verify CMF against manual calculation."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Candle where close == high (MFM = +1)
    c1 = Candle(ts, 100, 110, 90, 110, 10.0, "T/U", "1m")
    # Candle where close == low (MFM = -1)
    c2 = Candle(ts + timedelta(minutes=1), 110, 115, 95, 95, 20.0, "T/U", "1m")

    result = cmf_indicator.calculate([c1, c2], period=2)

    # MFV1 = ((110-90) - (110-110)) / (110-90) * 10 = 1.0 * 10 = 10
    # MFV2 = ((95-95) - (115-95)) / (115-95) * 20 = -1.0 * 20 = -20
    # CMF = (10 + (-20)) / (10 + 20) = -10/30 = -0.333...
    expected = -10.0 / 30.0
    assert result["cmf"][1] == pytest.approx(expected, rel=1e-6)


def test_cmf_evaluate_positive(cmf_indicator, sample_candles):
    """Positive should detect CMF > 0."""
    state = cmf_indicator.calculate(sample_candles)

    state["cmf"][-1] = 0.15
    assert cmf_indicator.evaluate(state, "positive") is True

    state["cmf"][-1] = -0.15
    assert cmf_indicator.evaluate(state, "positive") is False


def test_cmf_evaluate_negative(cmf_indicator, sample_candles):
    """Negative should detect CMF < 0."""
    state = cmf_indicator.calculate(sample_candles)

    state["cmf"][-1] = -0.15
    assert cmf_indicator.evaluate(state, "negative") is True

    state["cmf"][-1] = 0.15
    assert cmf_indicator.evaluate(state, "negative") is False


def test_cmf_evaluate_above(cmf_indicator, sample_candles):
    """Above should detect CMF > value."""
    state = cmf_indicator.calculate(sample_candles)

    state["cmf"][-1] = 0.3
    assert cmf_indicator.evaluate(state, "above", 0.2) is True
    assert cmf_indicator.evaluate(state, "above", 0.4) is False


def test_cmf_evaluate_below(cmf_indicator, sample_candles):
    """Below should detect CMF < value."""
    state = cmf_indicator.calculate(sample_candles)

    state["cmf"][-1] = -0.3
    assert cmf_indicator.evaluate(state, "below", -0.2) is True
    assert cmf_indicator.evaluate(state, "below", -0.4) is False


def test_cmf_evaluate_rising(cmf_indicator, sample_candles):
    """Rising should detect increasing CMF."""
    state = cmf_indicator.calculate(sample_candles)

    # Ensure last two values show rising
    n = len(state["cmf"])
    state["cmf"][n - 2] = 0.1
    state["cmf"][n - 1] = 0.2
    assert cmf_indicator.evaluate(state, "rising") is True


def test_cmf_evaluate_falling(cmf_indicator, sample_candles):
    """Falling should detect decreasing CMF."""
    state = cmf_indicator.calculate(sample_candles)

    n = len(state["cmf"])
    state["cmf"][n - 2] = 0.2
    state["cmf"][n - 1] = 0.1
    assert cmf_indicator.evaluate(state, "falling") is True


def test_cmf_update_matches_calculate(cmf_indicator, sample_candles):
    """Incremental update should match full calculation."""
    full = cmf_indicator.calculate(sample_candles, period=20)

    partial = cmf_indicator.calculate(sample_candles[:-1], period=20)
    updated = cmf_indicator.update(sample_candles[-1], partial, period=20)

    assert updated["cmf"][-1] == pytest.approx(full["cmf"][-1], rel=1e-6)


def test_cmf_unknown_operator(cmf_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = cmf_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        cmf_indicator.evaluate(state, "invalid_op")
