"""Tests for the Ichimoku Cloud indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle


@pytest.fixture
def ichimoku_indicator():
    """Return the registered Ichimoku indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("ichimoku")


def test_ichimoku_registered(ichimoku_indicator):
    """Ichimoku should be registered with correct attributes."""
    assert ichimoku_indicator.key == "ichimoku"
    assert ichimoku_indicator.category == "trend"
    assert ichimoku_indicator.name == "Ichimoku Cloud"


def test_ichimoku_default_params(ichimoku_indicator):
    """Default params should be tenkan=9, kijun=26, senkou_b=52, displacement=26."""
    p = ichimoku_indicator.default_params
    assert p["tenkan"] == 9
    assert p["kijun"] == 26
    assert p["senkou_b"] == 52
    assert p["displacement"] == 26


def test_ichimoku_calculate_structure(ichimoku_indicator, sample_candles):
    """calculate() should return all five Ichimoku lines."""
    result = ichimoku_indicator.calculate(sample_candles)
    for key in ("tenkan_sen", "kijun_sen", "senkou_a", "senkou_b", "chikou_span"):
        assert key in result
        assert len(result[key]) == len(sample_candles)


def test_ichimoku_tenkan_starts_at_correct_index(ichimoku_indicator, sample_candles):
    """Tenkan-sen should start at index tenkan-1 = 8."""
    result = ichimoku_indicator.calculate(sample_candles, tenkan=9)
    for i in range(8):
        assert result["tenkan_sen"][i] is None
    assert result["tenkan_sen"][8] is not None


def test_ichimoku_kijun_starts_at_correct_index(ichimoku_indicator, sample_candles):
    """Kijun-sen should start at index kijun-1 = 25."""
    result = ichimoku_indicator.calculate(sample_candles, kijun=26)
    for i in range(25):
        assert result["kijun_sen"][i] is None
    assert result["kijun_sen"][25] is not None


def test_ichimoku_tenkan_is_midpoint(ichimoku_indicator, sample_candles):
    """Tenkan-sen should be (highest high + lowest low) / 2 over tenkan period."""
    tenkan_p = 9
    result = ichimoku_indicator.calculate(sample_candles, tenkan=tenkan_p)
    idx = 50
    high = max(sample_candles[j].high for j in range(idx - tenkan_p + 1, idx + 1))
    low = min(sample_candles[j].low for j in range(idx - tenkan_p + 1, idx + 1))
    expected = (high + low) / 2.0
    assert result["tenkan_sen"][idx] == pytest.approx(expected, rel=1e-10)


def test_ichimoku_senkou_a_displaced(ichimoku_indicator, sample_candles):
    """Senkou A at displaced index should match (tenkan + kijun) / 2."""
    result = ichimoku_indicator.calculate(sample_candles)
    # Senkou A at index i+displacement was computed from tenkan/kijun at index i
    # So senkou_a at index 51 (=25+26) should be based on tenkan/kijun at 25
    displacement = 26
    src_idx = 25  # first index where both tenkan and kijun are valid
    target_idx = src_idx + displacement
    tenkan_val = result["tenkan_sen"][src_idx]
    kijun_val = result["kijun_sen"][src_idx]
    if tenkan_val is not None and kijun_val is not None and target_idx < len(sample_candles):
        expected = (tenkan_val + kijun_val) / 2.0
        assert result["senkou_a"][target_idx] == pytest.approx(expected, rel=1e-10)


def test_ichimoku_values_reasonable(ichimoku_indicator, sample_candles):
    """Ichimoku line values should be within reasonable range."""
    result = ichimoku_indicator.calculate(sample_candles)
    last_close = sample_candles[-1].close
    tenkan = result["tenkan_sen"][-1]
    kijun = result["kijun_sen"][-1]
    assert tenkan is not None
    assert kijun is not None
    assert abs(tenkan - last_close) < last_close * 0.05
    assert abs(kijun - last_close) < last_close * 0.05


def test_ichimoku_update_incremental(ichimoku_indicator, sample_candles):
    """Incremental update should produce valid tenkan/kijun values."""
    state = ichimoku_indicator.calculate(sample_candles[:-1])
    updated = ichimoku_indicator.update(sample_candles[-1], state)

    # Should have appended values
    assert len(updated["tenkan_sen"]) == len(sample_candles)
    assert updated["tenkan_sen"][-1] is not None


def test_ichimoku_evaluate_above_cloud(ichimoku_indicator, sample_candles):
    """above_cloud should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "above_cloud")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_below_cloud(ichimoku_indicator, sample_candles):
    """below_cloud should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "below_cloud")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_in_cloud(ichimoku_indicator, sample_candles):
    """in_cloud should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "in_cloud")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_tk_cross_up(ichimoku_indicator, sample_candles):
    """tk_cross_up should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "tk_cross_up")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_tk_cross_down(ichimoku_indicator, sample_candles):
    """tk_cross_down should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "tk_cross_down")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_cloud_green(ichimoku_indicator, sample_candles):
    """cloud_green should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "cloud_green")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_cloud_red(ichimoku_indicator, sample_candles):
    """cloud_red should return a bool."""
    state = ichimoku_indicator.calculate(sample_candles)
    result = ichimoku_indicator.evaluate(state, "cloud_red")
    assert isinstance(result, bool)


def test_ichimoku_evaluate_unknown(ichimoku_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = ichimoku_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        ichimoku_indicator.evaluate(state, "invalid_op")


def test_ichimoku_cloud_positions_mutually_exclusive(ichimoku_indicator, sample_candles):
    """Price should be in exactly one of: above_cloud, below_cloud, in_cloud
    (when cloud data is available).
    """
    state = ichimoku_indicator.calculate(sample_candles)
    above = ichimoku_indicator.evaluate(state, "above_cloud")
    below = ichimoku_indicator.evaluate(state, "below_cloud")
    in_cloud = ichimoku_indicator.evaluate(state, "in_cloud")

    # If we have cloud data, at most one should be True
    # (exactly one if all data is available)
    results = [above, below, in_cloud]
    true_count = sum(1 for r in results if r)
    # Could be 0 if no cloud data available
    assert true_count <= 1 or true_count == 1
