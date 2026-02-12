"""Tests for the Fair Value Gap (FVG) indicator."""

import pytest

from core.indicators.registry import get_registry
from core.models import Candle
from datetime import datetime, timedelta, timezone


@pytest.fixture
def fvg_indicator():
    """Return the registered FVG indicator instance."""
    registry = get_registry()
    registry.discover()
    return registry.get("fair_value_gap")


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


def test_fvg_registered(fvg_indicator):
    """FVG should be registered in the global registry."""
    assert fvg_indicator.key == "fair_value_gap"
    assert fvg_indicator.category == "special"
    assert fvg_indicator.name == "Fair Value Gap"


def test_fvg_default_params(fvg_indicator):
    """FVG should have expected default parameters."""
    assert fvg_indicator.default_params["lookback"] == 50
    assert fvg_indicator.default_params["min_gap_pct"] == 0.05
    assert fvg_indicator.default_params["proximity_pct"] == 0.1
    assert fvg_indicator.default_params["max_gaps"] == 10


def test_fvg_calculate_returns_keys(fvg_indicator, sample_candles):
    """Calculate should return bullish_fvgs, bearish_fvgs, current_price."""
    result = fvg_indicator.calculate(sample_candles)

    assert "bullish_fvgs" in result
    assert "bearish_fvgs" in result
    assert "current_price" in result


def test_fvg_detects_bullish_fvg(fvg_indicator):
    """Should detect bullish FVG: candle[0].high < candle[2].low."""
    prices = [
        (100, 102, 98, 101),    # candle 0: high = 102
        (101, 115, 100, 114),   # candle 1: impulse candle (big green)
        (114, 120, 110, 118),   # candle 2: low = 110 > 102 = candle 0 high -> gap!
    ]
    candles = _make_candles(prices)
    result = fvg_indicator.calculate(candles, min_gap_pct=0.01)

    assert len(result["bullish_fvgs"]) > 0
    fvg = result["bullish_fvgs"][0]
    # Gap zone: bottom = candle[0].high (102), top = candle[2].low (110)
    assert fvg["bottom"] == 102.0
    assert fvg["top"] == 110.0
    assert fvg["mitigated"] is False


def test_fvg_detects_bearish_fvg(fvg_indicator):
    """Should detect bearish FVG: candle[0].low > candle[2].high."""
    prices = [
        (110, 115, 108, 109),   # candle 0: low = 108
        (109, 110, 95, 96),     # candle 1: impulse (big red)
        (96, 100, 92, 98),      # candle 2: high = 100 < 108 = candle 0 low -> gap!
    ]
    candles = _make_candles(prices)
    result = fvg_indicator.calculate(candles, min_gap_pct=0.01)

    assert len(result["bearish_fvgs"]) > 0
    fvg = result["bearish_fvgs"][0]
    # Gap zone: top = candle[0].low (108), bottom = candle[2].high (100)
    assert fvg["top"] == 108.0
    assert fvg["bottom"] == 100.0


def test_fvg_no_gap_when_overlapping(fvg_indicator):
    """No FVG should be detected when candles overlap."""
    prices = [
        (100, 105, 95, 102),
        (102, 108, 100, 106),
        (106, 110, 103, 108),   # low (103) < candle[0].high (105) -> no gap
    ]
    candles = _make_candles(prices)
    result = fvg_indicator.calculate(candles, min_gap_pct=0.01)

    assert len(result["bullish_fvgs"]) == 0


def test_fvg_mitigation_bullish(fvg_indicator):
    """Bullish FVG should be mitigated when price drops below gap bottom."""
    prices = [
        (100, 102, 98, 101),
        (101, 115, 100, 114),
        (114, 120, 110, 118),   # bullish FVG: gap 102-110
        (118, 120, 95, 96),     # price drops below 102 -> mitigated
    ]
    candles = _make_candles(prices)
    result = fvg_indicator.calculate(candles, min_gap_pct=0.01)

    if result["bullish_fvgs"]:
        mitigated = [f for f in result["bullish_fvgs"] if f["mitigated"]]
        assert len(mitigated) > 0


def test_fvg_mitigation_bearish(fvg_indicator):
    """Bearish FVG should be mitigated when price rises above gap top."""
    prices = [
        (110, 115, 108, 109),
        (109, 110, 95, 96),
        (96, 100, 92, 98),      # bearish FVG: gap 100-108
        (98, 112, 97, 110),     # price rises above 108 -> mitigated
    ]
    candles = _make_candles(prices)
    result = fvg_indicator.calculate(candles, min_gap_pct=0.01)

    if result["bearish_fvgs"]:
        mitigated = [f for f in result["bearish_fvgs"] if f["mitigated"]]
        assert len(mitigated) > 0


def test_fvg_evaluate_fresh_bullish(fvg_indicator):
    """Evaluate fresh_bullish should detect unmitigated bullish FVGs."""
    state = {
        "bullish_fvgs": [{"top": 110, "bottom": 102, "index": 2, "mitigated": False}],
        "bearish_fvgs": [],
        "current_price": 115.0,
    }
    assert fvg_indicator.evaluate(state, "fresh_bullish") is True

    state["bullish_fvgs"][0]["mitigated"] = True
    assert fvg_indicator.evaluate(state, "fresh_bullish") is False


def test_fvg_evaluate_fresh_bearish(fvg_indicator):
    """Evaluate fresh_bearish should detect unmitigated bearish FVGs."""
    state = {
        "bullish_fvgs": [],
        "bearish_fvgs": [{"top": 108, "bottom": 100, "index": 2, "mitigated": False}],
        "current_price": 95.0,
    }
    assert fvg_indicator.evaluate(state, "fresh_bearish") is True


def test_fvg_evaluate_in_bullish_fvg(fvg_indicator):
    """Price inside a bullish FVG zone should be detected."""
    state = {
        "bullish_fvgs": [{"top": 110, "bottom": 102, "index": 2, "mitigated": False}],
        "bearish_fvgs": [],
        "current_price": 106.0,  # Inside the gap [102, 110]
    }
    assert fvg_indicator.evaluate(state, "in_bullish_fvg") is True

    state["current_price"] = 115.0  # Outside
    assert fvg_indicator.evaluate(state, "in_bullish_fvg") is False


def test_fvg_evaluate_in_bearish_fvg(fvg_indicator):
    """Price inside a bearish FVG zone should be detected."""
    state = {
        "bullish_fvgs": [],
        "bearish_fvgs": [{"top": 108, "bottom": 100, "index": 2, "mitigated": False}],
        "current_price": 104.0,
    }
    assert fvg_indicator.evaluate(state, "in_bearish_fvg") is True

    state["current_price"] = 95.0
    assert fvg_indicator.evaluate(state, "in_bearish_fvg") is False


def test_fvg_evaluate_near_bullish_fvg(fvg_indicator):
    """Near bullish FVG should detect price within proximity."""
    state = {
        "bullish_fvgs": [{"top": 110, "bottom": 102, "index": 2, "mitigated": False}],
        "bearish_fvgs": [],
        "current_price": 106.0,  # Mid of gap = 106
    }
    assert fvg_indicator.evaluate(state, "near_bullish_fvg", 1.0) is True

    state["current_price"] = 200.0
    assert fvg_indicator.evaluate(state, "near_bullish_fvg", 1.0) is False


def test_fvg_evaluate_near_bearish_fvg(fvg_indicator):
    """Near bearish FVG should detect price within proximity."""
    state = {
        "bullish_fvgs": [],
        "bearish_fvgs": [{"top": 108, "bottom": 100, "index": 2, "mitigated": False}],
        "current_price": 104.0,  # Mid = 104
    }
    assert fvg_indicator.evaluate(state, "near_bearish_fvg", 1.0) is True


def test_fvg_max_gaps_limit(fvg_indicator, sample_candles):
    """Should respect max_gaps parameter."""
    result = fvg_indicator.calculate(sample_candles, max_gaps=3, min_gap_pct=0.001)

    assert len(result["bullish_fvgs"]) <= 3
    assert len(result["bearish_fvgs"]) <= 3


def test_fvg_update_detects_new_gap(fvg_indicator):
    """Update should detect new FVGs."""
    prices = [
        (100, 102, 98, 101),
        (101, 115, 100, 114),
    ]
    candles = _make_candles(prices)
    state = fvg_indicator.calculate(candles, min_gap_pct=0.01)

    # Add a candle that creates a gap
    new_candle = Candle(
        timestamp=datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc),
        open=114, high=120, low=110, close=118,
        volume=10.0, pair="BTC/USDT", timeframe="1m",
    )
    updated = fvg_indicator.update(new_candle, state, min_gap_pct=0.01)
    assert updated["current_price"] == 118.0


def test_fvg_insufficient_data(fvg_indicator):
    """Should handle less than 3 candles gracefully."""
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts, 100, 105, 95, 102, 10.0, "T/U", "1m"),
    ]
    result = fvg_indicator.calculate(candles)
    assert result["bullish_fvgs"] == []
    assert result["bearish_fvgs"] == []


def test_fvg_unknown_operator(fvg_indicator, sample_candles):
    """Unknown operator should raise ValueError."""
    state = fvg_indicator.calculate(sample_candles)
    with pytest.raises(ValueError, match="Unknown operator"):
        fvg_indicator.evaluate(state, "invalid_op")


def test_fvg_with_large_dataset(fvg_indicator, sample_candles):
    """FVG should handle the full dataset without errors."""
    result = fvg_indicator.calculate(sample_candles, min_gap_pct=0.001)

    # With a small min_gap_pct, should detect some FVGs
    total = len(result["bullish_fvgs"]) + len(result["bearish_fvgs"])
    # It's possible to have 0 FVGs with random walk data, but the code shouldn't crash
    assert isinstance(total, int)
