"""Tests for the Bollinger Bands indicator."""

import math

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


def test_bollinger_calculate_returns_all_keys(bb_indicator, sample_candles):
    """Calculate should return upper, middle, lower, bandwidth, percent_b."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    assert "upper" in result
    assert "middle" in result
    assert "lower" in result
    assert "bandwidth" in result
    assert "percent_b" in result
    assert "prices" in result
    assert len(result["upper"]) == len(sample_candles)


def test_bollinger_warmup_period(bb_indicator, sample_candles):
    """First period-1 values should be None."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    for i in range(19):
        assert result["upper"][i] is None
        assert result["middle"][i] is None
        assert result["lower"][i] is None

    # After warmup, values should be present
    assert result["upper"][19] is not None
    assert result["middle"][19] is not None
    assert result["lower"][19] is not None


def test_bollinger_bands_relationship(bb_indicator, sample_candles):
    """Upper > middle > lower should always hold after warmup."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    for i in range(20, len(sample_candles)):
        upper = result["upper"][i]
        middle = result["middle"][i]
        lower = result["lower"][i]

        if upper is not None and middle is not None and lower is not None:
            assert upper > middle, f"At {i}: upper ({upper}) <= middle ({middle})"
            assert middle > lower, f"At {i}: middle ({middle}) <= lower ({lower})"


def test_bollinger_bandwidth_positive(bb_indicator, sample_candles):
    """Bandwidth should be positive after warmup."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    for i in range(20, len(sample_candles)):
        bw = result["bandwidth"][i]
        if bw is not None:
            assert bw >= 0


def test_bollinger_percent_b_range(bb_indicator, sample_candles):
    """Percent B should generally be between -0.5 and 1.5 for normal data."""
    result = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    for i in range(20, len(sample_candles)):
        pb = result["percent_b"][i]
        if pb is not None:
            # %B can exceed 0-1 range but should be reasonable
            assert -2.0 < pb < 3.0


def test_bollinger_middle_equals_sma(bb_indicator, sample_candles):
    """Middle band should equal the SMA."""
    period = 20
    result = bb_indicator.calculate(sample_candles, period=period, std_dev=2.0)

    # Manually compute SMA at a specific index
    idx = 30
    prices = [c.close for c in sample_candles]
    manual_sma = sum(prices[idx - period + 1 : idx + 1]) / period

    assert result["middle"][idx] == pytest.approx(manual_sma, rel=1e-6)


def test_bollinger_update_matches_calculate(bb_indicator, sample_candles):
    """Incremental update should match full calculation."""
    # Full calculation
    full = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Calculate without last candle, then update
    partial = bb_indicator.calculate(sample_candles[:-1], period=20, std_dev=2.0)
    updated = bb_indicator.update(sample_candles[-1], partial, period=20, std_dev=2.0)

    assert updated["upper"][-1] == pytest.approx(full["upper"][-1], rel=1e-6)
    assert updated["middle"][-1] == pytest.approx(full["middle"][-1], rel=1e-6)
    assert updated["lower"][-1] == pytest.approx(full["lower"][-1], rel=1e-6)


def test_bollinger_evaluate_touch_upper(bb_indicator, sample_candles):
    """Touch upper should detect price at/above upper band."""
    state = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Force price above upper band
    state["prices"][-1] = state["upper"][-1] + 100.0
    assert bb_indicator.evaluate(state, "touch_upper") is True

    # Force price below upper band
    state["prices"][-1] = state["upper"][-1] - 100.0
    assert bb_indicator.evaluate(state, "touch_upper") is False


def test_bollinger_evaluate_touch_lower(bb_indicator, sample_candles):
    """Touch lower should detect price at/below lower band."""
    state = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Force price below lower band
    state["prices"][-1] = state["lower"][-1] - 100.0
    assert bb_indicator.evaluate(state, "touch_lower") is True

    # Force price above lower band
    state["prices"][-1] = state["lower"][-1] + 100.0
    assert bb_indicator.evaluate(state, "touch_lower") is False


def test_bollinger_evaluate_squeeze(bb_indicator, sample_candles):
    """Squeeze should detect narrow bandwidth."""
    state = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Artificially set narrow bandwidth
    state["bandwidth"][-1] = 0.002
    assert bb_indicator.evaluate(state, "squeeze", 0.01) is True
    assert bb_indicator.evaluate(state, "squeeze", 0.001) is False


def test_bollinger_evaluate_expansion(bb_indicator, sample_candles):
    """Expansion should detect wide bandwidth."""
    state = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    state["bandwidth"][-1] = 0.05
    assert bb_indicator.evaluate(state, "expansion", 0.01) is True
    assert bb_indicator.evaluate(state, "expansion", 0.1) is False


def test_bollinger_evaluate_percent_b(bb_indicator, sample_candles):
    """Percent B operators should compare correctly."""
    state = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    state["percent_b"][-1] = 0.8
    assert bb_indicator.evaluate(state, "percent_b_above", 0.5) is True
    assert bb_indicator.evaluate(state, "percent_b_below", 0.5) is False

    state["percent_b"][-1] = 0.2
    assert bb_indicator.evaluate(state, "percent_b_below", 0.5) is True
    assert bb_indicator.evaluate(state, "percent_b_above", 0.5) is False


def test_bollinger_evaluate_inside(bb_indicator, sample_candles):
    """Inside should detect price between bands."""
    state = bb_indicator.calculate(sample_candles, period=20, std_dev=2.0)

    # Price between bands
    state["prices"][-1] = state["middle"][-1]
    assert bb_indicator.evaluate(state, "inside") is True


def test_bollinger_insufficient_data(bb_indicator):
    """Should handle insufficient data gracefully."""
    from datetime import datetime, timezone

    candles = [
        Candle(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open=100, high=105, low=95, close=102,
            volume=1.0, pair="BTC/USDT", timeframe="1m",
        )
    ]
    result = bb_indicator.calculate(candles, period=20)
    assert all(v is None for v in result["upper"])


def test_bollinger_unknown_operator(bb_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = bb_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        bb_indicator.evaluate(state, "invalid_op")
