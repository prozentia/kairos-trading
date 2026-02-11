"""Tests for the Bollinger Bands indicator.

These tests validate the Bollinger Bands implementation once built.
Tests that depend on unimplemented methods are skipped.
"""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def bb_indicator():
    """Return the registered Bollinger Bands indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("bollinger")


def test_bollinger_registered(bb_indicator):
    """Bollinger Bands should be registered in the global registry."""
    assert bb_indicator.key == "bollinger"
    assert bb_indicator.category == "volatility"
    assert bb_indicator.name == "Bollinger Bands"


def test_bollinger_default_params(bb_indicator):
    """Bollinger Bands should have default period=20 and std_dev=2.0."""
    assert bb_indicator.default_params["period"] == 20
    assert bb_indicator.default_params["std_dev"] == 2.0
    assert bb_indicator.default_params["source"] == "close"


@pytest.mark.skip(reason="BollingerBands.calculate() not implemented yet")
def test_bollinger_calculate(bb_indicator, sample_candles):
    """Bollinger calculation should return upper, middle, and lower bands."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    assert "upper" in result
    assert "middle" in result
    assert "lower" in result
    assert len(result["upper"]) == len(sample_candles)
    assert len(result["middle"]) == len(sample_candles)
    assert len(result["lower"]) == len(sample_candles)


@pytest.mark.skip(reason="BollingerBands.calculate() not implemented yet")
def test_bollinger_bands_relationship(bb_indicator, sample_candles):
    """Upper band > middle band > lower band should always hold."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Skip the warm-up period (first `period` candles may be None)
    for i in range(20, len(sample_candles)):
        upper = result["upper"][i]
        middle = result["middle"][i]
        lower = result["lower"][i]

        if upper is not None and middle is not None and lower is not None:
            assert upper > middle, f"At index {i}: upper ({upper}) should be > middle ({middle})"
            assert middle > lower, f"At index {i}: middle ({middle}) should be > lower ({lower})"
            # Bandwidth should be positive
            assert upper - lower > 0


@pytest.mark.skip(reason="BollingerBands.evaluate() not implemented yet")
def test_bollinger_squeeze_detection(bb_indicator, sample_candles):
    """Squeeze detection should identify low-volatility periods."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Simulate a squeeze state: very narrow bandwidth
    squeeze_state = dict(result)
    last_idx = len(sample_candles) - 1
    mid = squeeze_state["middle"][last_idx]
    # Artificially narrow the bands for testing
    squeeze_state["upper"][last_idx] = mid * 1.001
    squeeze_state["lower"][last_idx] = mid * 0.999
    squeeze_state["bandwidth"] = [None] * last_idx + [0.002]

    assert bb_indicator.evaluate(squeeze_state, "squeeze", 0.01) is True

    # Normal bandwidth should not trigger squeeze
    normal_state = dict(result)
    normal_state["bandwidth"] = [None] * last_idx + [0.05]
    assert bb_indicator.evaluate(normal_state, "squeeze", 0.01) is False
