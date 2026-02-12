"""Tests for the CandleBuffer circular buffer.

The buffer stores candles keyed by (pair, timeframe) with a configurable
maximum size, evicting the oldest candle when full.
"""

from datetime import datetime, timedelta, timezone

import pytest

from core.models import Candle
from core.timeframe.buffer import CandleBuffer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candle(
    pair: str = "BTC/USDT",
    timeframe: str = "5m",
    close: float = 97_500.0,
    minute_offset: int = 0,
) -> Candle:
    """Create a minimal candle."""
    ts = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minute_offset)
    return Candle(
        timestamp=ts,
        open=close - 50,
        high=close + 100,
        low=close - 100,
        close=close,
        volume=5.0,
        pair=pair,
        timeframe=timeframe,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCandleBufferInit:
    """Test buffer initialization."""

    def test_default_max_size(self):
        buf = CandleBuffer()
        assert buf.max_size == 1000

    def test_custom_max_size(self):
        buf = CandleBuffer(max_size=500)
        assert buf.max_size == 500

    def test_invalid_max_size(self):
        with pytest.raises(ValueError):
            CandleBuffer(max_size=0)
        with pytest.raises(ValueError):
            CandleBuffer(max_size=-1)


class TestAdd:
    """Test adding candles to the buffer."""

    def test_add_single(self):
        buf = CandleBuffer(max_size=10)
        c = _candle()
        buf.add(c)
        assert buf.size("BTC/USDT", "5m") == 1

    def test_add_multiple(self):
        buf = CandleBuffer(max_size=10)
        for i in range(5):
            buf.add(_candle(minute_offset=i))
        assert buf.size("BTC/USDT", "5m") == 5

    def test_eviction_on_overflow(self):
        buf = CandleBuffer(max_size=3)
        for i in range(5):
            buf.add(_candle(close=97_000.0 + i * 100, minute_offset=i))
        assert buf.size("BTC/USDT", "5m") == 3
        # Oldest candles should be evicted.
        all_candles = buf.get_all("BTC/USDT", "5m")
        assert all_candles[0].close == 97_200.0  # 3rd candle added
        assert all_candles[-1].close == 97_400.0  # 5th candle added


class TestGetLast:
    """Test retrieving the last N candles."""

    def test_get_last_basic(self):
        buf = CandleBuffer(max_size=10)
        for i in range(5):
            buf.add(_candle(close=97_000.0 + i * 100, minute_offset=i))

        last_3 = buf.get_last(3, "BTC/USDT", "5m")
        assert len(last_3) == 3
        assert last_3[0].close == 97_200.0
        assert last_3[-1].close == 97_400.0

    def test_get_last_more_than_available(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle())
        last_5 = buf.get_last(5, "BTC/USDT", "5m")
        assert len(last_5) == 1

    def test_get_last_empty_buffer(self):
        buf = CandleBuffer(max_size=10)
        result = buf.get_last(5, "BTC/USDT", "5m")
        assert result == []

    def test_get_last_nonexistent_key(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT"))
        result = buf.get_last(5, "ETH/USDT", "5m")
        assert result == []


class TestGetAll:
    """Test retrieving all candles."""

    def test_get_all_basic(self):
        buf = CandleBuffer(max_size=10)
        for i in range(5):
            buf.add(_candle(minute_offset=i))
        all_candles = buf.get_all("BTC/USDT", "5m")
        assert len(all_candles) == 5

    def test_get_all_empty(self):
        buf = CandleBuffer(max_size=10)
        assert buf.get_all("BTC/USDT", "5m") == []


class TestMultipleKeys:
    """Test that different pairs/timeframes are stored separately."""

    def test_separate_pairs(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT"))
        buf.add(_candle(pair="ETH/USDT"))
        assert buf.size("BTC/USDT", "5m") == 1
        assert buf.size("ETH/USDT", "5m") == 1

    def test_separate_timeframes(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(timeframe="5m"))
        buf.add(_candle(timeframe="15m"))
        assert buf.size("BTC/USDT", "5m") == 1
        assert buf.size("BTC/USDT", "15m") == 1


class TestMetadata:
    """Test pairs() and timeframes() lookups."""

    def test_pairs(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT"))
        buf.add(_candle(pair="ETH/USDT"))
        buf.add(_candle(pair="BTC/USDT"))
        pairs = buf.pairs()
        assert sorted(pairs) == ["BTC/USDT", "ETH/USDT"]

    def test_timeframes(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT", timeframe="1m"))
        buf.add(_candle(pair="BTC/USDT", timeframe="5m"))
        buf.add(_candle(pair="BTC/USDT", timeframe="1h"))
        tfs = buf.timeframes("BTC/USDT")
        assert sorted(tfs) == ["1h", "1m", "5m"]


class TestClear:
    """Test clearing buffer data."""

    def test_clear_all(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT"))
        buf.add(_candle(pair="ETH/USDT"))
        buf.clear()
        assert buf.size("BTC/USDT", "5m") == 0
        assert buf.size("ETH/USDT", "5m") == 0

    def test_clear_by_pair(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT"))
        buf.add(_candle(pair="ETH/USDT"))
        buf.clear(pair="BTC/USDT")
        assert buf.size("BTC/USDT", "5m") == 0
        assert buf.size("ETH/USDT", "5m") == 1

    def test_clear_by_pair_and_timeframe(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle(pair="BTC/USDT", timeframe="5m"))
        buf.add(_candle(pair="BTC/USDT", timeframe="15m"))
        buf.clear(pair="BTC/USDT", timeframe="5m")
        assert buf.size("BTC/USDT", "5m") == 0
        assert buf.size("BTC/USDT", "15m") == 1


class TestRepr:
    """Test string representation."""

    def test_repr(self):
        buf = CandleBuffer(max_size=10)
        buf.add(_candle())
        r = repr(buf)
        assert "CandleBuffer" in r
        assert "keys=1" in r
        assert "candles=1" in r
