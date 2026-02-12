"""Tests for the ADX/DMI indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def adx_indicator():
    """Return the registered ADX/DMI indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("adx_dmi")


def test_adx_registered(adx_indicator):
    """ADX/DMI should be registered with correct attributes."""
    assert adx_indicator.key == "adx_dmi"
    assert adx_indicator.category == "volatility"
    assert adx_indicator.name == "ADX / DMI"


def test_adx_default_params(adx_indicator):
    """Default params should have period=14."""
    assert adx_indicator.default_params["period"] == 14


def test_adx_calculate_structure(adx_indicator, sample_candles):
    """calculate() should return adx, plus_di, minus_di lists."""
    result = adx_indicator.calculate(sample_candles)
    assert "adx" in result
    assert "plus_di" in result
    assert "minus_di" in result
    assert len(result["adx"]) == len(sample_candles)
    assert len(result["plus_di"]) == len(sample_candles)
    assert len(result["minus_di"]) == len(sample_candles)


def test_adx_none_before_warmup(adx_indicator, sample_candles):
    """ADX values before warmup period (2*period) should be None."""
    period = 14
    result = adx_indicator.calculate(sample_candles, period=period)
    # ADX needs 2*period of data
    for i in range(period):
        assert result["adx"][i] is None


def test_adx_di_starts_at_period(adx_indicator, sample_candles):
    """+DI and -DI should start at index = period."""
    period = 14
    result = adx_indicator.calculate(sample_candles, period=period)
    assert result["plus_di"][period] is not None
    assert result["minus_di"][period] is not None


def test_adx_has_values_after_warmup(adx_indicator, sample_candles):
    """ADX should have values after full warmup."""
    result = adx_indicator.calculate(sample_candles)
    assert result["adx"][-1] is not None
    assert result["plus_di"][-1] is not None
    assert result["minus_di"][-1] is not None


def test_adx_values_range(adx_indicator, sample_candles):
    """ADX, +DI, -DI should all be between 0 and 100."""
    result = adx_indicator.calculate(sample_candles)
    for key in ("adx", "plus_di", "minus_di"):
        for v in result[key]:
            if v is not None:
                assert 0 <= v <= 100, f"{key} value {v} out of [0, 100]"


def test_adx_di_sum_reasonable(adx_indicator, sample_candles):
    """+DI and -DI should not both be 0 in a trending market."""
    result = adx_indicator.calculate(sample_candles)
    # Check the last value
    pdi = result["plus_di"][-1]
    mdi = result["minus_di"][-1]
    assert pdi is not None and mdi is not None
    assert pdi + mdi > 0  # At least one should be positive


def test_adx_update_incremental(adx_indicator, sample_candles):
    """Incremental update should produce valid ADX values."""
    state = adx_indicator.calculate(sample_candles[:-1])
    updated = adx_indicator.update(sample_candles[-1], state)

    assert updated["adx"][-1] is not None
    assert updated["plus_di"][-1] is not None
    assert updated["minus_di"][-1] is not None


def test_adx_update_values_close(adx_indicator, sample_candles):
    """Incremental update values should be close to full recalculation."""
    state = adx_indicator.calculate(sample_candles[:-1])
    updated = adx_indicator.update(sample_candles[-1], state)

    full = adx_indicator.calculate(sample_candles)

    # +DI and -DI should match closely
    assert updated["plus_di"][-1] == pytest.approx(full["plus_di"][-1], rel=1e-4)
    assert updated["minus_di"][-1] == pytest.approx(full["minus_di"][-1], rel=1e-4)


def test_adx_evaluate_trending(adx_indicator, sample_candles):
    """trending should return True when ADX > threshold."""
    state = adx_indicator.calculate(sample_candles)
    adx_val = state["adx"][-1]
    result = adx_indicator.evaluate(state, "trending", value=adx_val - 1)
    assert result is True


def test_adx_evaluate_not_trending(adx_indicator, sample_candles):
    """not_trending should return True when ADX < threshold."""
    state = adx_indicator.calculate(sample_candles)
    adx_val = state["adx"][-1]
    result = adx_indicator.evaluate(state, "not_trending", value=adx_val + 1)
    assert result is True


def test_adx_evaluate_bullish(adx_indicator, sample_candles):
    """bullish should return True when +DI > -DI."""
    state = adx_indicator.calculate(sample_candles)
    result = adx_indicator.evaluate(state, "bullish")
    pdi = state["plus_di"][-1]
    mdi = state["minus_di"][-1]
    expected = pdi > mdi
    assert result == expected


def test_adx_evaluate_bearish(adx_indicator, sample_candles):
    """bearish should return True when -DI > +DI."""
    state = adx_indicator.calculate(sample_candles)
    result = adx_indicator.evaluate(state, "bearish")
    pdi = state["plus_di"][-1]
    mdi = state["minus_di"][-1]
    expected = mdi > pdi
    assert result == expected


def test_adx_evaluate_di_cross_up(adx_indicator, sample_candles):
    """di_cross_up should return a bool."""
    state = adx_indicator.calculate(sample_candles)
    result = adx_indicator.evaluate(state, "di_cross_up")
    assert isinstance(result, bool)


def test_adx_evaluate_di_cross_down(adx_indicator, sample_candles):
    """di_cross_down should return a bool."""
    state = adx_indicator.calculate(sample_candles)
    result = adx_indicator.evaluate(state, "di_cross_down")
    assert isinstance(result, bool)


def test_adx_evaluate_unknown(adx_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = adx_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        adx_indicator.evaluate(state, "invalid_op")


def test_adx_insufficient_candles(adx_indicator, sample_candles):
    """With very few candles, all values should be None."""
    result = adx_indicator.calculate(sample_candles[:5], period=14)
    assert all(v is None for v in result["adx"])
