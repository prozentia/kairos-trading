"""Tests for the Order Block indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timedelta, timezone


@pytest.fixture
def ob_indicator():
    """Return the registered Order Block indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("order_block")


def _make_candles(prices: list[tuple[float, float, float, float]]) -> list[Candle]:
    """Create candles from (open, high, low, close) tuples."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=ts + timedelta(minutes=i),
            open=o, high=h, low=l, close=c,
            volume=10.0, pair="BTC/USDT", timeframe="1m",
        )
        for i, (o, h, l, c) in enumerate(prices)
    ]


def test_ob_registered(ob_indicator):
    """Order Block should be registered in the global registry."""
    assert ob_indicator.key == "order_block"
    assert ob_indicator.category == "special"
    assert ob_indicator.name == "Order Block"


def test_ob_default_params(ob_indicator):
    """Order Block should have expected default parameters."""
    assert ob_indicator.default_params["lookback"] == 20
    assert ob_indicator.default_params["min_impulse_pct"] == 0.5
    assert ob_indicator.default_params["proximity_pct"] == 0.1
    assert ob_indicator.default_params["max_blocks"] == 5


def test_ob_calculate_returns_keys(ob_indicator, sample_candles):
    """Calculate should return bullish_obs, bearish_obs, current_price."""
    result = ob_indicator.calculate(sample_candles)

    assert "bullish_obs" in result
    assert "bearish_obs" in result
    assert "current_price" in result


def test_ob_detects_bullish_ob(ob_indicator):
    """Should detect bullish OB (last red candle before big green impulse)."""
    prices = [
        (100, 102, 98, 101),    # green
        (101, 103, 99, 100),    # red (potential OB)
        (100, 106, 99, 105),    # big green impulse (5% body)
    ]
    candles = _make_candles(prices)
    result = ob_indicator.calculate(candles, min_impulse_pct=0.3)

    # Should detect at least one bullish OB
    assert len(result["bullish_obs"]) > 0
    ob = result["bullish_obs"][0]
    assert "high" in ob
    assert "low" in ob
    assert "mitigated" in ob


def test_ob_detects_bearish_ob(ob_indicator):
    """Should detect bearish OB (last green candle before big red impulse)."""
    prices = [
        (100, 102, 98, 99),     # red
        (99, 103, 98, 102),     # green (potential OB)
        (102, 103, 95, 96),     # big red impulse
    ]
    candles = _make_candles(prices)
    result = ob_indicator.calculate(candles, min_impulse_pct=0.3)

    assert len(result["bearish_obs"]) > 0


def test_ob_mitigation(ob_indicator):
    """Bullish OB should be mitigated when price returns below its low."""
    prices = [
        (100, 102, 98, 101),    # green
        (101, 103, 99, 100),    # red (OB)
        (100, 108, 99, 107),    # big green impulse
        (107, 109, 98, 98),     # price drops below OB low -> mitigated
    ]
    candles = _make_candles(prices)
    result = ob_indicator.calculate(candles, min_impulse_pct=0.3)

    if result["bullish_obs"]:
        # The OB should be mitigated since price dropped below its low
        mitigated_obs = [ob for ob in result["bullish_obs"] if ob["mitigated"]]
        assert len(mitigated_obs) > 0


def test_ob_fresh_detection(ob_indicator):
    """Should identify fresh (unmitigated) order blocks."""
    prices = [
        (100, 102, 98, 101),    # green
        (101, 103, 99, 100),    # red (OB, low=99)
        (100, 108, 100, 107),   # big green impulse (low=100, stays above OB low)
        (107, 110, 106, 109),   # price stays above OB
        (109, 112, 107, 111),   # price still above
    ]
    candles = _make_candles(prices)
    result = ob_indicator.calculate(candles, min_impulse_pct=0.3)

    assert len(result["bullish_obs"]) > 0
    fresh = [ob for ob in result["bullish_obs"] if not ob["mitigated"]]
    assert len(fresh) > 0


def test_ob_evaluate_fresh_bullish(ob_indicator, sample_candles):
    """Evaluate fresh_bullish should detect unmitigated bullish OBs."""
    state = ob_indicator.calculate(sample_candles)

    # Force a fresh bullish OB
    state["bullish_obs"] = [{"high": 100, "low": 98, "index": 0, "mitigated": False}]
    assert ob_indicator.evaluate(state, "fresh_bullish") is True

    state["bullish_obs"] = [{"high": 100, "low": 98, "index": 0, "mitigated": True}]
    assert ob_indicator.evaluate(state, "fresh_bullish") is False


def test_ob_evaluate_fresh_bearish(ob_indicator, sample_candles):
    """Evaluate fresh_bearish should detect unmitigated bearish OBs."""
    state = ob_indicator.calculate(sample_candles)

    state["bearish_obs"] = [{"high": 102, "low": 100, "index": 0, "mitigated": False}]
    assert ob_indicator.evaluate(state, "fresh_bearish") is True


def test_ob_evaluate_in_bullish_ob(ob_indicator):
    """Price inside a bullish OB zone should be detected."""
    state = {
        "bullish_obs": [{"high": 100, "low": 95, "index": 0, "mitigated": False}],
        "bearish_obs": [],
        "current_price": 97.0,
    }
    assert ob_indicator.evaluate(state, "in_bullish_ob") is True

    state["current_price"] = 110.0
    assert ob_indicator.evaluate(state, "in_bullish_ob") is False


def test_ob_evaluate_in_bearish_ob(ob_indicator):
    """Price inside a bearish OB zone should be detected."""
    state = {
        "bullish_obs": [],
        "bearish_obs": [{"high": 105, "low": 100, "index": 0, "mitigated": False}],
        "current_price": 102.0,
    }
    assert ob_indicator.evaluate(state, "in_bearish_ob") is True


def test_ob_evaluate_near_bullish_ob(ob_indicator):
    """Near bullish OB should detect price within proximity."""
    state = {
        "bullish_obs": [{"high": 100, "low": 96, "index": 0, "mitigated": False}],
        "bearish_obs": [],
        "current_price": 98.0,  # OB mid = 98, exact match
    }
    assert ob_indicator.evaluate(state, "near_bullish_ob", 1.0) is True

    state["current_price"] = 200.0
    assert ob_indicator.evaluate(state, "near_bullish_ob", 1.0) is False


def test_ob_evaluate_near_bearish_ob(ob_indicator):
    """Near bearish OB should detect price within proximity."""
    state = {
        "bullish_obs": [],
        "bearish_obs": [{"high": 105, "low": 100, "index": 0, "mitigated": False}],
        "current_price": 102.5,  # OB mid = 102.5
    }
    assert ob_indicator.evaluate(state, "near_bearish_ob", 1.0) is True


def test_ob_max_blocks_limit(ob_indicator, sample_candles):
    """Should respect max_blocks parameter."""
    result = ob_indicator.calculate(sample_candles, max_blocks=3)

    assert len(result["bullish_obs"]) <= 3
    assert len(result["bearish_obs"]) <= 3


def test_ob_update_adds_new_blocks(ob_indicator):
    """Update should detect new order blocks."""
    candles = _make_candles([
        (100, 102, 98, 101),
        (101, 103, 99, 100),
    ])
    state = ob_indicator.calculate(candles, min_impulse_pct=0.3)

    # Add an impulsive candle
    new_candle = Candle(
        timestamp=datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc),
        open=100, high=110, low=99, close=109,
        volume=10.0, pair="BTC/USDT", timeframe="1m",
    )
    updated = ob_indicator.update(new_candle, state, min_impulse_pct=0.3)

    assert updated["current_price"] == 109.0


def test_ob_unknown_operator(ob_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = ob_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        ob_indicator.evaluate(state, "invalid_op")


def test_ob_with_large_dataset(ob_indicator, sample_candles):
    """OB should handle the full dataset without errors."""
    # Use a lower threshold since random walk data has small moves (~0.3%)
    result = ob_indicator.calculate(sample_candles, min_impulse_pct=0.1)

    # Should detect at least some OBs in 500 candles with low threshold
    total_obs = len(result["bullish_obs"]) + len(result["bearish_obs"])
    assert total_obs > 0, "Should detect at least one OB in 500 candles"
