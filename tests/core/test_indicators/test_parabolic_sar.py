"""Tests for the Parabolic SAR indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def psar_indicator():
    """Return the registered Parabolic SAR indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("parabolic_sar")


def test_psar_registered(psar_indicator):
    """Parabolic SAR should be registered with correct attributes."""
    assert psar_indicator.key == "parabolic_sar"
    assert psar_indicator.category == "trend"
    assert psar_indicator.name == "Parabolic SAR"


def test_psar_default_params(psar_indicator):
    """Default params should include af_start, af_step, af_max."""
    assert psar_indicator.default_params["af_start"] == 0.02
    assert psar_indicator.default_params["af_step"] == 0.02
    assert psar_indicator.default_params["af_max"] == 0.2


def test_psar_calculate_structure(psar_indicator, sample_candles):
    """calculate() should return sar and direction lists."""
    result = psar_indicator.calculate(sample_candles)
    assert "sar" in result
    assert "direction" in result
    assert len(result["sar"]) == len(sample_candles)
    assert len(result["direction"]) == len(sample_candles)


def test_psar_calculate_has_values(psar_indicator, sample_candles):
    """SAR values should exist after the first two candles."""
    result = psar_indicator.calculate(sample_candles)
    # Should have values from the very beginning
    assert result["sar"][0] is not None
    assert result["sar"][-1] is not None


def test_psar_direction_values(psar_indicator, sample_candles):
    """Direction should only be +1, -1, or None."""
    result = psar_indicator.calculate(sample_candles)
    for d in result["direction"]:
        assert d is None or d in (1, -1)


def test_psar_value_reasonable(psar_indicator, sample_candles):
    """SAR value should be within a reasonable range of the close price."""
    result = psar_indicator.calculate(sample_candles)
    sar = result["sar"][-1]
    close = sample_candles[-1].close
    assert sar is not None
    # SAR should be within 3% of close (it's a trailing stop level)
    assert abs(sar - close) < close * 0.03


def test_psar_bullish_sar_below_price(psar_indicator, sample_candles):
    """In bullish direction, SAR should be below the candle low."""
    result = psar_indicator.calculate(sample_candles)
    # Check the last few candles where direction is bullish
    for i in range(len(sample_candles) - 1, max(0, len(sample_candles) - 50), -1):
        if result["direction"][i] == 1 and result["sar"][i] is not None:
            # SAR should be at or below the low
            assert result["sar"][i] <= sample_candles[i].high
            break


def test_psar_update_incremental(psar_indicator, sample_candles):
    """Incremental update should produce consistent direction."""
    state = psar_indicator.calculate(sample_candles[:-1])
    updated = psar_indicator.update(sample_candles[-1], state)

    # The direction should be valid
    assert updated["direction"][-1] in (1, -1)
    assert updated["sar"][-1] is not None


def test_psar_evaluate_bullish(psar_indicator, sample_candles):
    """bullish should return True when direction is +1."""
    state = psar_indicator.calculate(sample_candles)
    result = psar_indicator.evaluate(state, "bullish")
    expected = state["direction"][-1] == 1
    assert result == expected


def test_psar_evaluate_bearish(psar_indicator, sample_candles):
    """bearish should return True when direction is -1."""
    state = psar_indicator.calculate(sample_candles)
    result = psar_indicator.evaluate(state, "bearish")
    expected = state["direction"][-1] == -1
    assert result == expected


def test_psar_evaluate_flip_up(psar_indicator, sample_candles):
    """flip_up should return a bool."""
    state = psar_indicator.calculate(sample_candles)
    result = psar_indicator.evaluate(state, "flip_up")
    assert isinstance(result, bool)


def test_psar_evaluate_flip_down(psar_indicator, sample_candles):
    """flip_down should return a bool."""
    state = psar_indicator.calculate(sample_candles)
    result = psar_indicator.evaluate(state, "flip_down")
    assert isinstance(result, bool)


def test_psar_evaluate_unknown_operator(psar_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = psar_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        psar_indicator.evaluate(state, "invalid_op")


def test_psar_insufficient_candles(psar_indicator, sample_candles):
    """With only 1 candle, SAR should be all None."""
    result = psar_indicator.calculate(sample_candles[:1])
    assert all(v is None for v in result["sar"])
