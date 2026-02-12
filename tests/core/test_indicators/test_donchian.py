"""Tests for the Donchian Channel indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def donchian_indicator():
    """Return the registered Donchian Channel indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("donchian")


def test_donchian_registered(donchian_indicator):
    """Donchian should be registered with correct attributes."""
    assert donchian_indicator.key == "donchian"
    assert donchian_indicator.category == "trend"
    assert donchian_indicator.name == "Donchian Channel"


def test_donchian_default_params(donchian_indicator):
    """Default params should have period=20."""
    assert donchian_indicator.default_params["period"] == 20


def test_donchian_calculate_structure(donchian_indicator, sample_candles):
    """calculate() should return upper, lower, middle, width lists."""
    result = donchian_indicator.calculate(sample_candles)
    for key in ("upper", "lower", "middle", "width"):
        assert key in result
        assert len(result[key]) == len(sample_candles)


def test_donchian_none_before_period(donchian_indicator, sample_candles):
    """Values before period should be None."""
    result = donchian_indicator.calculate(sample_candles, period=20)
    for i in range(18):
        assert result["upper"][i] is None
    assert result["upper"][19] is not None


def test_donchian_upper_ge_lower(donchian_indicator, sample_candles):
    """Upper band should always be >= lower band."""
    result = donchian_indicator.calculate(sample_candles)
    for i in range(len(sample_candles)):
        if result["upper"][i] is not None:
            assert result["upper"][i] >= result["lower"][i]


def test_donchian_middle_is_average(donchian_indicator, sample_candles):
    """Middle should be (upper + lower) / 2."""
    result = donchian_indicator.calculate(sample_candles)
    for i in range(len(sample_candles)):
        if result["upper"][i] is not None:
            expected = (result["upper"][i] + result["lower"][i]) / 2.0
            assert result["middle"][i] == pytest.approx(expected, rel=1e-10)


def test_donchian_width_positive(donchian_indicator, sample_candles):
    """Width should always be >= 0."""
    result = donchian_indicator.calculate(sample_candles)
    for w in result["width"]:
        if w is not None:
            assert w >= 0


def test_donchian_upper_is_highest_high(donchian_indicator, sample_candles):
    """Upper band should be the highest high in the window."""
    period = 20
    result = donchian_indicator.calculate(sample_candles, period=period)
    idx = 50  # check a specific index
    expected = max(sample_candles[j].high for j in range(idx - period + 1, idx + 1))
    assert result["upper"][idx] == pytest.approx(expected, rel=1e-10)


def test_donchian_lower_is_lowest_low(donchian_indicator, sample_candles):
    """Lower band should be the lowest low in the window."""
    period = 20
    result = donchian_indicator.calculate(sample_candles, period=period)
    idx = 50
    expected = min(sample_candles[j].low for j in range(idx - period + 1, idx + 1))
    assert result["lower"][idx] == pytest.approx(expected, rel=1e-10)


def test_donchian_update_incremental(donchian_indicator, sample_candles):
    """Incremental update should match full calculation."""
    state = donchian_indicator.calculate(sample_candles[:-1], period=20)
    updated = donchian_indicator.update(sample_candles[-1], state, period=20)

    full = donchian_indicator.calculate(sample_candles, period=20)

    assert updated["upper"][-1] == pytest.approx(full["upper"][-1], rel=1e-6)
    assert updated["lower"][-1] == pytest.approx(full["lower"][-1], rel=1e-6)


def test_donchian_evaluate_breakout_up(donchian_indicator, sample_candles):
    """breakout_up should be True when close >= upper."""
    state = donchian_indicator.calculate(sample_candles)
    state["current_close"] = state["upper"][-1]
    assert donchian_indicator.evaluate(state, "breakout_up") is True


def test_donchian_evaluate_breakout_down(donchian_indicator, sample_candles):
    """breakout_down should be True when close <= lower."""
    state = donchian_indicator.calculate(sample_candles)
    state["current_close"] = state["lower"][-1]
    assert donchian_indicator.evaluate(state, "breakout_down") is True


def test_donchian_evaluate_inside(donchian_indicator, sample_candles):
    """inside should be True when lower < close < upper."""
    state = donchian_indicator.calculate(sample_candles)
    state["current_close"] = state["middle"][-1]
    assert donchian_indicator.evaluate(state, "inside") is True


def test_donchian_evaluate_squeeze(donchian_indicator, sample_candles):
    """squeeze should return a bool."""
    state = donchian_indicator.calculate(sample_candles)
    result = donchian_indicator.evaluate(state, "squeeze")
    assert isinstance(result, bool)


def test_donchian_evaluate_unknown(donchian_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = donchian_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        donchian_indicator.evaluate(state, "invalid_op")


def test_donchian_insufficient_candles(donchian_indicator, sample_candles):
    """With fewer candles than period, all values should be None."""
    result = donchian_indicator.calculate(sample_candles[:5], period=20)
    assert all(v is None for v in result["upper"])
