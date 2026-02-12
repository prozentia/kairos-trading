"""Tests for the Keltner Channel indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timezone


@pytest.fixture
def keltner_indicator():
    """Return the registered Keltner Channel indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("keltner")


def test_keltner_registered(keltner_indicator):
    """Keltner Channel should be registered in the global registry."""
    assert keltner_indicator.key == "keltner"
    assert keltner_indicator.category == "volatility"
    assert keltner_indicator.name == "Keltner Channel"


def test_keltner_default_params(keltner_indicator):
    """Keltner should have default ema_period=20, atr_period=10, multiplier=1.5."""
    assert keltner_indicator.default_params["ema_period"] == 20
    assert keltner_indicator.default_params["atr_period"] == 10
    assert keltner_indicator.default_params["multiplier"] == 1.5


def test_keltner_calculate_returns_keys(keltner_indicator, sample_candles):
    """Calculate should return upper, middle, lower, atr, prices."""
    result = keltner_indicator.calculate(sample_candles)

    assert "upper" in result
    assert "middle" in result
    assert "lower" in result
    assert "atr" in result
    assert "prices" in result
    assert len(result["upper"]) == len(sample_candles)


def test_keltner_bands_relationship(keltner_indicator, sample_candles):
    """Upper > middle > lower should hold when both EMA and ATR are available."""
    result = keltner_indicator.calculate(sample_candles)

    for i in range(len(sample_candles)):
        u = result["upper"][i]
        m = result["middle"][i]
        l = result["lower"][i]
        if u is not None and m is not None and l is not None:
            assert u > m, f"At {i}: upper ({u}) <= middle ({m})"
            assert m > l, f"At {i}: middle ({m}) <= lower ({l})"


def test_keltner_warmup_period(keltner_indicator, sample_candles):
    """Values should be None during warmup."""
    result = keltner_indicator.calculate(
        sample_candles, ema_period=20, atr_period=10
    )

    # Before both EMA and ATR are ready, values should be None
    for i in range(10):
        assert result["upper"][i] is None


def test_keltner_evaluate_touch_upper(keltner_indicator, sample_candles):
    """Touch upper should detect price at/above upper channel."""
    state = keltner_indicator.calculate(sample_candles)

    # Find the last valid upper value
    last_upper = None
    for v in reversed(state["upper"]):
        if v is not None:
            last_upper = v
            break

    # Force price above upper
    state["prices"][-1] = last_upper + 100.0
    assert keltner_indicator.evaluate(state, "touch_upper") is True

    # Force price below upper
    state["prices"][-1] = last_upper - 100.0
    assert keltner_indicator.evaluate(state, "touch_upper") is False


def test_keltner_evaluate_touch_lower(keltner_indicator, sample_candles):
    """Touch lower should detect price at/below lower channel."""
    state = keltner_indicator.calculate(sample_candles)

    last_lower = None
    for v in reversed(state["lower"]):
        if v is not None:
            last_lower = v
            break

    state["prices"][-1] = last_lower - 100.0
    assert keltner_indicator.evaluate(state, "touch_lower") is True

    state["prices"][-1] = last_lower + 100.0
    assert keltner_indicator.evaluate(state, "touch_lower") is False


def test_keltner_evaluate_inside(keltner_indicator, sample_candles):
    """Inside should detect price between channels."""
    state = keltner_indicator.calculate(sample_candles)

    last_middle = None
    for v in reversed(state["middle"]):
        if v is not None:
            last_middle = v
            break

    state["prices"][-1] = last_middle
    assert keltner_indicator.evaluate(state, "inside") is True


def test_keltner_evaluate_squeeze_with_bb(keltner_indicator, sample_candles):
    """Squeeze should detect when BB bands are inside Keltner channels."""
    state = keltner_indicator.calculate(sample_candles)

    last_upper = None
    last_lower = None
    for v in reversed(state["upper"]):
        if v is not None:
            last_upper = v
            break
    for v in reversed(state["lower"]):
        if v is not None:
            last_lower = v
            break

    # BB inside Keltner = squeeze
    bb_data = {
        "bb_upper": last_upper - 10.0,
        "bb_lower": last_lower + 10.0,
    }
    assert keltner_indicator.evaluate(state, "squeeze_with_bb", bb_data) is True

    # BB outside Keltner = no squeeze
    bb_data = {
        "bb_upper": last_upper + 100.0,
        "bb_lower": last_lower - 100.0,
    }
    assert keltner_indicator.evaluate(state, "squeeze_with_bb", bb_data) is False


def test_keltner_update_produces_values(keltner_indicator, sample_candles):
    """Incremental update should produce new values."""
    partial = keltner_indicator.calculate(sample_candles[:-1])
    partial["_prev_close"] = sample_candles[-2].close

    updated = keltner_indicator.update(sample_candles[-1], partial)

    # Should have one more value
    assert len(updated["upper"]) == len(sample_candles)
    assert updated["upper"][-1] is not None


def test_keltner_unknown_operator(keltner_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = keltner_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        keltner_indicator.evaluate(state, "invalid_op")


def test_keltner_empty_candles(keltner_indicator):
    """Should handle empty candle list."""
    result = keltner_indicator.calculate([])
    assert result["upper"] == []
    assert result["middle"] == []
