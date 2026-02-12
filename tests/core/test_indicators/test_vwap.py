"""Tests for the VWAP (Volume Weighted Average Price) indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timedelta, timezone


@pytest.fixture
def vwap_indicator():
    """Return the registered VWAP indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("vwap")


def test_vwap_registered(vwap_indicator):
    """VWAP should be registered in the global registry."""
    assert vwap_indicator.key == "vwap"
    assert vwap_indicator.category == "volume"
    assert vwap_indicator.name == "Volume Weighted Average Price"


def test_vwap_default_params(vwap_indicator):
    """VWAP should have default reset_period and band_multiplier."""
    assert vwap_indicator.default_params["reset_period"] == "session"
    assert vwap_indicator.default_params["band_multiplier"] == 2.0


def test_vwap_calculate_returns_keys(vwap_indicator, sample_candles):
    """Calculate should return vwap, upper_band, lower_band, prices."""
    result = vwap_indicator.calculate(sample_candles)

    assert "vwap" in result
    assert "upper_band" in result
    assert "lower_band" in result
    assert "prices" in result
    assert len(result["vwap"]) == len(sample_candles)


def test_vwap_first_value(vwap_indicator):
    """First VWAP value should equal the typical price of first candle."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts, 100, 110, 90, 105, 10.0, "T/U", "1m"),
    ]
    result = vwap_indicator.calculate(candles)

    # TP = (110 + 90 + 105) / 3 = 101.666...
    expected = (110 + 90 + 105) / 3.0
    assert result["vwap"][0] == pytest.approx(expected, rel=1e-6)


def test_vwap_manual_calculation(vwap_indicator):
    """Verify VWAP against manual calculation."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts, 100, 110, 90, 105, 10.0, "T/U", "1m"),
        Candle(ts + timedelta(minutes=1), 105, 115, 100, 112, 20.0, "T/U", "1m"),
    ]
    result = vwap_indicator.calculate(candles)

    tp1 = (110 + 90 + 105) / 3.0
    tp2 = (115 + 100 + 112) / 3.0

    expected_vwap = (tp1 * 10.0 + tp2 * 20.0) / (10.0 + 20.0)
    assert result["vwap"][1] == pytest.approx(expected_vwap, rel=1e-6)


def test_vwap_all_values_present(vwap_indicator, sample_candles):
    """VWAP should have values for every candle."""
    result = vwap_indicator.calculate(sample_candles)

    for val in result["vwap"]:
        assert val is not None


def test_vwap_bands_relationship(vwap_indicator, sample_candles):
    """Upper band > VWAP > lower band should hold."""
    result = vwap_indicator.calculate(sample_candles)

    for i in range(1, len(sample_candles)):
        v = result["vwap"][i]
        u = result["upper_band"][i]
        l = result["lower_band"][i]
        if v is not None and u is not None and l is not None:
            assert u >= v, f"At {i}: upper ({u}) < vwap ({v})"
            assert v >= l, f"At {i}: vwap ({v}) < lower ({l})"


def test_vwap_evaluate_price_above(vwap_indicator, sample_candles):
    """Price above should detect when close > VWAP."""
    state = vwap_indicator.calculate(sample_candles)

    state["prices"][-1] = state["vwap"][-1] + 100.0
    assert vwap_indicator.evaluate(state, "price_above") is True

    state["prices"][-1] = state["vwap"][-1] - 100.0
    assert vwap_indicator.evaluate(state, "price_above") is False


def test_vwap_evaluate_price_below(vwap_indicator, sample_candles):
    """Price below should detect when close < VWAP."""
    state = vwap_indicator.calculate(sample_candles)

    state["prices"][-1] = state["vwap"][-1] - 100.0
    assert vwap_indicator.evaluate(state, "price_below") is True

    state["prices"][-1] = state["vwap"][-1] + 100.0
    assert vwap_indicator.evaluate(state, "price_below") is False


def test_vwap_evaluate_cross_up(vwap_indicator, sample_candles):
    """Cross up should detect price crossing above VWAP."""
    state = vwap_indicator.calculate(sample_candles)

    # Set up a cross up scenario
    vwap_val = state["vwap"][-1]
    state["prices"][-2] = vwap_val - 10.0
    state["prices"][-1] = vwap_val + 10.0
    state["vwap"][-2] = vwap_val

    assert vwap_indicator.evaluate(state, "cross_up") is True


def test_vwap_evaluate_cross_down(vwap_indicator, sample_candles):
    """Cross down should detect price crossing below VWAP."""
    state = vwap_indicator.calculate(sample_candles)

    vwap_val = state["vwap"][-1]
    state["prices"][-2] = vwap_val + 10.0
    state["prices"][-1] = vwap_val - 10.0
    state["vwap"][-2] = vwap_val

    assert vwap_indicator.evaluate(state, "cross_down") is True


def test_vwap_evaluate_deviation(vwap_indicator, sample_candles):
    """Deviation should measure percentage distance from VWAP."""
    state = vwap_indicator.calculate(sample_candles)

    vwap_val = state["vwap"][-1]
    # Set price 2% above VWAP
    state["prices"][-1] = vwap_val * 1.02
    assert vwap_indicator.evaluate(state, "deviation", 1.0) is True
    assert vwap_indicator.evaluate(state, "deviation", 3.0) is False


def test_vwap_update_matches_calculate(vwap_indicator, sample_candles):
    """Incremental update should match full calculation."""
    full = vwap_indicator.calculate(sample_candles)

    partial = vwap_indicator.calculate(sample_candles[:-1])
    # Transfer cumulative state
    n_partial = len(sample_candles) - 1
    cumtpv = 0.0
    cumvol = 0.0
    cumtpv2 = 0.0
    for c in sample_candles[:-1]:
        tp = (c.high + c.low + c.close) / 3.0
        cumtpv += tp * c.volume
        cumvol += c.volume
        cumtpv2 += tp * tp * c.volume
    partial["_cumulative_tpv"] = cumtpv
    partial["_cumulative_vol"] = cumvol
    partial["_cumulative_tpv2"] = cumtpv2

    updated = vwap_indicator.update(sample_candles[-1], partial)

    assert updated["vwap"][-1] == pytest.approx(full["vwap"][-1], rel=1e-6)


def test_vwap_unknown_operator(vwap_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = vwap_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        vwap_indicator.evaluate(state, "invalid_op")


def test_vwap_empty_candles(vwap_indicator):
    """Should handle empty candle list."""
    result = vwap_indicator.calculate([])
    assert result["vwap"] == []
