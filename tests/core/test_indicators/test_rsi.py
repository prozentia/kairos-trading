"""Tests for the RSI (Relative Strength Index) indicator.

These tests validate the RSI implementation once built. Tests that
depend on unimplemented methods are skipped with a clear reason.
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


def test_rsi_registered(rsi_indicator):
    """RSI should be registered in the global registry."""
    assert rsi_indicator.key == "rsi"
    assert rsi_indicator.category == "momentum"
    assert rsi_indicator.name == "Relative Strength Index"


def test_rsi_default_params(rsi_indicator):
    """RSI should have default period=14 and source=close."""
    assert rsi_indicator.default_params["period"] == 14
    assert rsi_indicator.default_params["source"] == "close"


@pytest.mark.skip(reason="RSI.calculate() not implemented yet")
def test_rsi_calculate(rsi_indicator, sample_candles):
    """RSI calculation should return values in the range [0, 100]."""
    result = rsi_indicator.calculate(sample_candles, period=14)
    assert "rsi" in result
    rsi_values = result["rsi"]
    assert len(rsi_values) == len(sample_candles)

    # All computed (non-None) values should be in [0, 100]
    for val in rsi_values:
        if val is not None:
            assert 0.0 <= val <= 100.0, f"RSI value {val} is out of range"


@pytest.mark.skip(reason="RSI.evaluate() not implemented yet")
def test_rsi_overbought(rsi_indicator):
    """RSI above 70 should be detected as overbought."""
    state = {"rsi": [None] * 13 + [75.0], "current_rsi": 75.0}
    assert rsi_indicator.evaluate(state, "above", 70) is True
    assert rsi_indicator.evaluate(state, "above", 80) is False


@pytest.mark.skip(reason="RSI.evaluate() not implemented yet")
def test_rsi_oversold(rsi_indicator):
    """RSI below 30 should be detected as oversold."""
    state = {"rsi": [None] * 13 + [25.0], "current_rsi": 25.0}
    assert rsi_indicator.evaluate(state, "below", 30) is True
    assert rsi_indicator.evaluate(state, "below", 20) is False


@pytest.mark.skip(reason="RSI.calculate() not implemented yet")
def test_rsi_range(rsi_indicator, sample_candles):
    """RSI values should always be between 0 and 100 inclusive."""
    result = rsi_indicator.calculate(sample_candles, period=14)
    rsi_values = [v for v in result["rsi"] if v is not None]
    assert len(rsi_values) > 0
    assert all(0.0 <= v <= 100.0 for v in rsi_values), "RSI values should be in [0, 100]"
    # RSI should not all be the same value (sanity check)
    assert len(set(rsi_values)) > 1, "RSI values should vary across different candles"
