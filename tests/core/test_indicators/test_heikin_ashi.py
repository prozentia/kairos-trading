"""Tests for the Heikin-Ashi indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle, HeikinAshi
from datetime import datetime, timedelta, timezone


@pytest.fixture
def ha_indicator():
    """Return the registered Heikin-Ashi indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("heikin_ashi")


def test_ha_registered(ha_indicator):
    """Heikin-Ashi should be registered in the global registry."""
    assert ha_indicator.key == "heikin_ashi"
    assert ha_indicator.category == "trend"
    assert ha_indicator.name == "Heikin Ashi"


def test_ha_calculate_returns_keys(ha_indicator, sample_candles):
    """Calculate should return ha_candles, is_green, consecutive counts."""
    result = ha_indicator.calculate(sample_candles)

    assert "ha_candles" in result
    assert "is_green" in result
    assert "consecutive_green" in result
    assert "consecutive_red" in result
    assert len(result["ha_candles"]) == len(sample_candles)
    assert len(result["is_green"]) == len(sample_candles)


def test_ha_candle_type(ha_indicator, sample_candles):
    """HA candles should be HeikinAshi instances."""
    result = ha_indicator.calculate(sample_candles)

    for ha in result["ha_candles"]:
        assert isinstance(ha, HeikinAshi)


def test_ha_first_candle_formula(ha_indicator):
    """First HA candle should follow the initialization formula."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts, 100, 110, 90, 105, 10.0, "T/U", "1m"),
    ]
    result = ha_indicator.calculate(candles)

    ha = result["ha_candles"][0]
    # Close = (O + H + L + C) / 4 = (100 + 110 + 90 + 105) / 4 = 101.25
    assert ha.close == pytest.approx(101.25, rel=1e-6)
    # Open = (O + C) / 2 = (100 + 105) / 2 = 102.5
    assert ha.open == pytest.approx(102.5, rel=1e-6)
    # High = max(110, 102.5, 101.25) = 110
    assert ha.high == pytest.approx(110.0, rel=1e-6)
    # Low = min(90, 102.5, 101.25) = 90
    assert ha.low == pytest.approx(90.0, rel=1e-6)


def test_ha_second_candle_formula(ha_indicator):
    """Second HA candle should use previous HA open/close for its open."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts, 100, 110, 90, 105, 10.0, "T/U", "1m"),
        Candle(ts + timedelta(minutes=1), 105, 115, 100, 112, 15.0, "T/U", "1m"),
    ]
    result = ha_indicator.calculate(candles)

    ha0 = result["ha_candles"][0]
    ha1 = result["ha_candles"][1]

    # HA1 Open = (HA0.Open + HA0.Close) / 2
    expected_open = (ha0.open + ha0.close) / 2.0
    assert ha1.open == pytest.approx(expected_open, rel=1e-6)

    # HA1 Close = (105 + 115 + 100 + 112) / 4 = 108
    assert ha1.close == pytest.approx(108.0, rel=1e-6)


def test_ha_is_green_detection(ha_indicator):
    """Green should be detected when HA close > HA open."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Create candles that produce a green HA candle
    candles = [
        Candle(ts, 100, 110, 90, 105, 10.0, "T/U", "1m"),
        Candle(ts + timedelta(minutes=1), 105, 120, 100, 118, 15.0, "T/U", "1m"),
    ]
    result = ha_indicator.calculate(candles)

    # The second candle should be green (strong up move)
    ha1 = result["ha_candles"][1]
    assert ha1.close > ha1.open
    assert result["is_green"][1] is True


def test_ha_consecutive_count(ha_indicator, sample_candles):
    """Consecutive green/red count should be at least 1."""
    result = ha_indicator.calculate(sample_candles)

    cg = result["consecutive_green"]
    cr = result["consecutive_red"]

    # Exactly one of them should be > 0
    assert (cg > 0) or (cr > 0)
    # They should not both be > 0
    assert not (cg > 0 and cr > 0)


def test_ha_evaluate_is_green(ha_indicator, sample_candles):
    """Evaluate is_green should check the last HA candle color."""
    state = ha_indicator.calculate(sample_candles)

    last_green = state["is_green"][-1]
    assert ha_indicator.evaluate(state, "is_green") is last_green


def test_ha_evaluate_is_red(ha_indicator, sample_candles):
    """Evaluate is_red should be the opposite of is_green."""
    state = ha_indicator.calculate(sample_candles)

    last_green = state["is_green"][-1]
    assert ha_indicator.evaluate(state, "is_red") is (not last_green)


def test_ha_evaluate_flip_to_green(ha_indicator):
    """Flip to green should detect red -> green transition."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Build candles that go from red to green
    candles = [
        Candle(ts, 110, 112, 95, 96, 10.0, "T/U", "1m"),    # Down
        Candle(ts + timedelta(minutes=1), 96, 97, 88, 90, 10.0, "T/U", "1m"),    # Down
        Candle(ts + timedelta(minutes=2), 90, 115, 89, 114, 20.0, "T/U", "1m"),  # Strong up
    ]
    state = ha_indicator.calculate(candles)

    # The transition should be detectable
    if not state["is_green"][-2] and state["is_green"][-1]:
        assert ha_indicator.evaluate(state, "flip_to_green") is True


def test_ha_evaluate_consecutive_green(ha_indicator, sample_candles):
    """Consecutive green should check against a threshold."""
    state = ha_indicator.calculate(sample_candles)

    state["consecutive_green"] = 5
    assert ha_indicator.evaluate(state, "consecutive_green", 3) is True
    assert ha_indicator.evaluate(state, "consecutive_green", 7) is False


def test_ha_evaluate_consecutive_red(ha_indicator, sample_candles):
    """Consecutive red should check against a threshold."""
    state = ha_indicator.calculate(sample_candles)

    state["consecutive_red"] = 4
    assert ha_indicator.evaluate(state, "consecutive_red", 3) is True
    assert ha_indicator.evaluate(state, "consecutive_red", 5) is False


def test_ha_update_matches_calculate(ha_indicator, sample_candles):
    """Incremental update should match full calculation."""
    full = ha_indicator.calculate(sample_candles)

    partial = ha_indicator.calculate(sample_candles[:-1])
    updated = ha_indicator.update(sample_candles[-1], partial)

    full_last = full["ha_candles"][-1]
    upd_last = updated["ha_candles"][-1]

    assert upd_last.open == pytest.approx(full_last.open, rel=1e-6)
    assert upd_last.close == pytest.approx(full_last.close, rel=1e-6)
    assert upd_last.high == pytest.approx(full_last.high, rel=1e-6)
    assert upd_last.low == pytest.approx(full_last.low, rel=1e-6)
    assert upd_last.is_green == full_last.is_green


def test_ha_unknown_operator(ha_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = ha_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        ha_indicator.evaluate(state, "invalid_op")


def test_ha_empty_candles(ha_indicator):
    """Should handle empty candle list."""
    result = ha_indicator.calculate([])
    assert result["ha_candles"] == []
    assert result["is_green"] == []
    assert result["consecutive_green"] == 0
    assert result["consecutive_red"] == 0


def test_ha_preserves_pair_and_timeframe(ha_indicator, sample_candles):
    """HA candles should preserve pair and timeframe from original."""
    result = ha_indicator.calculate(sample_candles)

    for ha, original in zip(result["ha_candles"], sample_candles):
        assert ha.pair == original.pair
        assert ha.timeframe == original.timeframe
