"""Tests for the Volume Analysis indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timedelta, timezone


@pytest.fixture
def vol_indicator():
    """Return the registered Volume indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("volume")


def test_volume_registered(vol_indicator):
    """Volume should be registered in the global registry."""
    assert vol_indicator.key == "volume"
    assert vol_indicator.category == "volume"
    assert vol_indicator.name == "Volume Analysis"


def test_volume_default_params(vol_indicator):
    """Volume should have default ma_period=20, spike_multiplier=2.0."""
    assert vol_indicator.default_params["ma_period"] == 20
    assert vol_indicator.default_params["spike_multiplier"] == 2.0


def test_volume_calculate_returns_keys(vol_indicator, sample_candles):
    """Calculate should return volumes, vol_sma, vol_ratio, obv."""
    result = vol_indicator.calculate(sample_candles)

    assert "volumes" in result
    assert "vol_sma" in result
    assert "vol_ratio" in result
    assert "obv" in result
    assert len(result["volumes"]) == len(sample_candles)
    assert len(result["obv"]) == len(sample_candles)


def test_volume_obv_calculation(vol_indicator):
    """OBV should increase on up candles and decrease on down candles."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts, 100, 105, 95, 102, 10.0, "T/U", "1m"),
        Candle(ts + timedelta(minutes=1), 102, 108, 100, 106, 15.0, "T/U", "1m"),  # Up
        Candle(ts + timedelta(minutes=2), 106, 107, 100, 100, 20.0, "T/U", "1m"),  # Down
        Candle(ts + timedelta(minutes=3), 100, 105, 98, 104, 5.0, "T/U", "1m"),    # Up
    ]

    result = vol_indicator.calculate(candles, ma_period=2)

    # OBV[0] = 10
    assert result["obv"][0] == 10.0
    # OBV[1] = 10 + 15 = 25 (close went up)
    assert result["obv"][1] == 25.0
    # OBV[2] = 25 - 20 = 5 (close went down)
    assert result["obv"][2] == 5.0
    # OBV[3] = 5 + 5 = 10 (close went up)
    assert result["obv"][3] == 10.0


def test_volume_sma(vol_indicator, sample_candles):
    """Volume SMA should equal the average of the window."""
    result = vol_indicator.calculate(sample_candles, ma_period=20)

    # Verify SMA at a specific point
    idx = 30
    volumes = [c.volume for c in sample_candles]
    manual_sma = sum(volumes[idx - 19 : idx + 1]) / 20

    assert result["vol_sma"][idx] == pytest.approx(manual_sma, rel=1e-6)


def test_volume_ratio(vol_indicator, sample_candles):
    """Volume ratio should be volume / SMA."""
    result = vol_indicator.calculate(sample_candles, ma_period=20)

    idx = 30
    if result["vol_sma"][idx] is not None and result["vol_sma"][idx] > 0:
        expected_ratio = result["volumes"][idx] / result["vol_sma"][idx]
        assert result["vol_ratio"][idx] == pytest.approx(expected_ratio, rel=1e-6)


def test_volume_evaluate_above_average(vol_indicator, sample_candles):
    """Above average should detect when ratio > 1."""
    state = vol_indicator.calculate(sample_candles)

    # Force high ratio
    state["vol_ratio"][-1] = 1.5
    assert vol_indicator.evaluate(state, "above_average") is True

    state["vol_ratio"][-1] = 0.5
    assert vol_indicator.evaluate(state, "above_average") is False


def test_volume_evaluate_below_average(vol_indicator, sample_candles):
    """Below average should detect when ratio < 1."""
    state = vol_indicator.calculate(sample_candles)

    state["vol_ratio"][-1] = 0.5
    assert vol_indicator.evaluate(state, "below_average") is True

    state["vol_ratio"][-1] = 1.5
    assert vol_indicator.evaluate(state, "below_average") is False


def test_volume_evaluate_spike(vol_indicator, sample_candles):
    """Spike should detect when ratio > multiplier."""
    state = vol_indicator.calculate(sample_candles)

    state["vol_ratio"][-1] = 3.0
    assert vol_indicator.evaluate(state, "spike", 2.0) is True
    assert vol_indicator.evaluate(state, "spike", 4.0) is False


def test_volume_evaluate_obv_rising(vol_indicator, sample_candles):
    """OBV rising should detect increasing OBV."""
    state = vol_indicator.calculate(sample_candles)

    state["obv"][-2] = 100.0
    state["obv"][-1] = 120.0
    assert vol_indicator.evaluate(state, "obv_rising") is True

    state["obv"][-1] = 80.0
    assert vol_indicator.evaluate(state, "obv_rising") is False


def test_volume_evaluate_obv_falling(vol_indicator, sample_candles):
    """OBV falling should detect decreasing OBV."""
    state = vol_indicator.calculate(sample_candles)

    state["obv"][-2] = 120.0
    state["obv"][-1] = 100.0
    assert vol_indicator.evaluate(state, "obv_falling") is True


def test_volume_evaluate_dry_up(vol_indicator, sample_candles):
    """Dry up should detect very low volume."""
    state = vol_indicator.calculate(sample_candles)

    state["vol_ratio"][-1] = 0.3
    assert vol_indicator.evaluate(state, "dry_up", 0.5) is True

    state["vol_ratio"][-1] = 0.8
    assert vol_indicator.evaluate(state, "dry_up", 0.5) is False


def test_volume_update_matches_calculate(vol_indicator, sample_candles):
    """Incremental update should produce consistent OBV."""
    full = vol_indicator.calculate(sample_candles)

    partial = vol_indicator.calculate(sample_candles[:-1])
    partial["_prev_close"] = sample_candles[-2].close
    updated = vol_indicator.update(sample_candles[-1], partial)

    assert updated["obv"][-1] == pytest.approx(full["obv"][-1], rel=1e-6)


def test_volume_unknown_operator(vol_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = vol_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        vol_indicator.evaluate(state, "invalid_op")
