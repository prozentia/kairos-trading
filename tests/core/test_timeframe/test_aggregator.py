"""Tests for the TimeframeAggregator.

The aggregator receives 1m candles one at a time and emits completed
candles for higher timeframes (5m, 15m, 1h, etc.).
"""

from datetime import datetime, timedelta, timezone

import pytest

from core.models import Candle
from core.timeframe.aggregator import TimeframeAggregator, TIMEFRAME_MINUTES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candle_1m(
    minute: int,
    hour: int = 12,
    open_price: float = 97_500.0,
    close_price: float = 97_550.0,
    high_price: float = 97_600.0,
    low_price: float = 97_400.0,
    volume: float = 3.0,
    pair: str = "BTC/USDT",
) -> Candle:
    """Create a 1m candle at a specific minute of the hour."""
    return Candle(
        timestamp=datetime(2026, 2, 10, hour, minute, 0, tzinfo=timezone.utc),
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        pair=pair,
        timeframe="1m",
        is_closed=True,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    """Test aggregator initialization."""

    def test_default_timeframes(self):
        agg = TimeframeAggregator()
        assert agg.target_timeframes == ["5m", "15m", "1h"]

    def test_custom_timeframes(self):
        agg = TimeframeAggregator(target_timeframes=["3m", "30m"])
        assert agg.target_timeframes == ["3m", "30m"]

    def test_invalid_timeframe(self):
        with pytest.raises(ValueError, match="Unknown timeframe"):
            TimeframeAggregator(target_timeframes=["99m"])

    def test_cannot_aggregate_to_1m(self):
        with pytest.raises(ValueError, match="must be > 1m"):
            TimeframeAggregator(target_timeframes=["1m"])

    def test_rejects_non_1m_input(self):
        agg = TimeframeAggregator(target_timeframes=["5m"])
        candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            open=97_500, high=97_600, low=97_400, close=97_550,
            volume=3.0, pair="BTC/USDT", timeframe="5m",
        )
        with pytest.raises(ValueError, match="Expected 1m"):
            agg.on_candle(candle)


# ---------------------------------------------------------------------------
# 5m aggregation
# ---------------------------------------------------------------------------

class TestAggregate5m:
    """Test aggregation of 1m candles into 5m candles."""

    def test_five_candles_produce_one_5m(self):
        """5 consecutive 1m candles at minutes 0-4 should produce one 5m candle."""
        agg = TimeframeAggregator(target_timeframes=["5m"])
        completed = []

        for m in range(5):
            result = agg.on_candle(
                _candle_1m(
                    minute=m,
                    open_price=97_500.0 + m * 10,
                    close_price=97_510.0 + m * 10,
                    high_price=97_600.0 + m * 10,
                    low_price=97_400.0 - m * 5,
                    volume=1.0 + m,
                )
            )
            completed.extend(result)

        assert len(completed) == 1
        c5 = completed[0]
        assert c5.timeframe == "5m"
        assert c5.pair == "BTC/USDT"
        assert c5.is_closed is True

    def test_5m_ohlcv_values(self):
        """The 5m candle should have correct OHLCV values."""
        agg = TimeframeAggregator(target_timeframes=["5m"])
        completed = []

        opens = [100, 110, 120, 130, 140]
        closes = [105, 115, 125, 135, 145]
        highs = [108, 118, 128, 138, 150]
        lows = [95, 105, 115, 125, 130]
        volumes = [1.0, 2.0, 3.0, 4.0, 5.0]

        for i, m in enumerate(range(5)):
            result = agg.on_candle(
                _candle_1m(
                    minute=m,
                    open_price=opens[i],
                    close_price=closes[i],
                    high_price=highs[i],
                    low_price=lows[i],
                    volume=volumes[i],
                )
            )
            completed.extend(result)

        assert len(completed) == 1
        c = completed[0]
        assert c.open == 100       # First candle's open.
        assert c.close == 145      # Last candle's close.
        assert c.high == 150       # Max of all highs.
        assert c.low == 95         # Min of all lows.
        assert c.volume == pytest.approx(15.0)  # Sum of volumes.

    def test_no_output_before_boundary(self):
        """First 4 candles of a 5m period should produce no output."""
        agg = TimeframeAggregator(target_timeframes=["5m"])
        for m in range(4):
            result = agg.on_candle(_candle_1m(minute=m))
            assert len(result) == 0

    def test_two_consecutive_periods(self):
        """Two complete 5m periods should produce two candles."""
        agg = TimeframeAggregator(target_timeframes=["5m"])
        completed = []

        for m in range(10):
            result = agg.on_candle(_candle_1m(minute=m))
            completed.extend(result)

        assert len(completed) == 2


# ---------------------------------------------------------------------------
# 15m aggregation
# ---------------------------------------------------------------------------

class TestAggregate15m:
    """Test aggregation into 15m candles."""

    def test_fifteen_candles_produce_one_15m(self):
        agg = TimeframeAggregator(target_timeframes=["15m"])
        completed = []

        for m in range(15):
            result = agg.on_candle(_candle_1m(minute=m))
            completed.extend(result)

        assert len(completed) == 1
        assert completed[0].timeframe == "15m"


# ---------------------------------------------------------------------------
# 1h aggregation
# ---------------------------------------------------------------------------

class TestAggregate1h:
    """Test aggregation into 1h candles."""

    def test_sixty_candles_produce_one_1h(self):
        agg = TimeframeAggregator(target_timeframes=["1h"])
        completed = []

        for m in range(60):
            result = agg.on_candle(_candle_1m(minute=m, hour=12))
            completed.extend(result)

        assert len(completed) == 1
        assert completed[0].timeframe == "1h"


# ---------------------------------------------------------------------------
# Multi-timeframe
# ---------------------------------------------------------------------------

class TestMultiTimeframe:
    """Test aggregation into multiple timeframes simultaneously."""

    def test_5m_and_15m_together(self):
        """Running 15 candles should produce 3x 5m + 1x 15m."""
        agg = TimeframeAggregator(target_timeframes=["5m", "15m"])
        completed = []

        for m in range(15):
            result = agg.on_candle(_candle_1m(minute=m))
            completed.extend(result)

        five_min = [c for c in completed if c.timeframe == "5m"]
        fifteen_min = [c for c in completed if c.timeframe == "15m"]
        assert len(five_min) == 3
        assert len(fifteen_min) == 1


# ---------------------------------------------------------------------------
# Multiple pairs
# ---------------------------------------------------------------------------

class TestMultiplePairs:
    """Test that different pairs are aggregated independently."""

    def test_two_pairs_separate(self):
        agg = TimeframeAggregator(target_timeframes=["5m"])
        btc_completed = []
        eth_completed = []

        for m in range(5):
            r1 = agg.on_candle(_candle_1m(minute=m, pair="BTC/USDT"))
            r2 = agg.on_candle(_candle_1m(minute=m, pair="ETH/USDT"))
            btc_completed.extend(c for c in r1 if c.pair == "BTC/USDT")
            eth_completed.extend(c for c in r2 if c.pair == "ETH/USDT")

        assert len(btc_completed) == 1
        assert len(eth_completed) == 1


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:
    """Test resetting the aggregator buffers."""

    def test_reset_all(self):
        agg = TimeframeAggregator(target_timeframes=["5m"])
        for m in range(3):
            agg.on_candle(_candle_1m(minute=m))
        agg.reset()
        # After reset, sending the remaining 2 candles should NOT produce output
        # because the buffer was cleared and we don't have a full period.
        completed = []
        for m in range(3, 5):
            result = agg.on_candle(_candle_1m(minute=m))
            completed.extend(result)
        # The first candle after reset will start at minute 3 which is
        # within the 0-4 period. minute 4 is the last -> should complete.
        assert len(completed) == 1

    def test_reset_by_pair(self):
        agg = TimeframeAggregator(target_timeframes=["5m"])
        for m in range(3):
            agg.on_candle(_candle_1m(minute=m, pair="BTC/USDT"))
            agg.on_candle(_candle_1m(minute=m, pair="ETH/USDT"))

        agg.reset(pair="BTC/USDT")

        # BTC buffer is cleared; ETH buffer still has 3 candles.
        # Continue ETH to complete its period.
        eth_completed = []
        for m in range(3, 5):
            result = agg.on_candle(_candle_1m(minute=m, pair="ETH/USDT"))
            eth_completed.extend(result)
        assert len(eth_completed) == 1


# ---------------------------------------------------------------------------
# Period start alignment
# ---------------------------------------------------------------------------

class TestPeriodStart:
    """Test the _period_start helper."""

    def test_5m_alignment(self):
        agg = TimeframeAggregator(target_timeframes=["5m"])
        ts = datetime(2026, 2, 10, 12, 7, 30, tzinfo=timezone.utc)
        start = agg._period_start(ts, 5)
        assert start.hour == 12
        assert start.minute == 5

    def test_15m_alignment(self):
        agg = TimeframeAggregator(target_timeframes=["15m"])
        ts = datetime(2026, 2, 10, 12, 23, 0, tzinfo=timezone.utc)
        start = agg._period_start(ts, 15)
        assert start.hour == 12
        assert start.minute == 15

    def test_1h_alignment(self):
        agg = TimeframeAggregator(target_timeframes=["1h"])
        ts = datetime(2026, 2, 10, 12, 45, 0, tzinfo=timezone.utc)
        start = agg._period_start(ts, 60)
        assert start.hour == 12
        assert start.minute == 0

    def test_midnight_boundary(self):
        agg = TimeframeAggregator(target_timeframes=["5m"])
        ts = datetime(2026, 2, 10, 0, 3, 0, tzinfo=timezone.utc)
        start = agg._period_start(ts, 5)
        assert start.hour == 0
        assert start.minute == 0
