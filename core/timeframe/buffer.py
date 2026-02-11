"""Candle buffer -- circular buffer for historical candle storage.

Provides fast access to the last N candles per (pair, timeframe) key
without unbounded memory growth.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from core.models import Candle


class CandleBuffer:
    """In-memory circular buffer for candle data.

    Stores candles keyed by (pair, timeframe) with a configurable
    maximum size per key.

    Usage::

        buf = CandleBuffer(max_size=500)
        buf.add(candle)
        last_20 = buf.get_last(20, pair="BTC/USDT", timeframe="5m")
    """

    def __init__(self, max_size: int = 1000) -> None:
        """
        Args:
            max_size: Maximum number of candles to keep per
                      (pair, timeframe) combination.
        """
        if max_size <= 0:
            raise ValueError("max_size must be a positive integer.")
        self.max_size = max_size
        self._buffers: dict[tuple[str, str], deque[Candle]] = defaultdict(
            lambda: deque(maxlen=max_size)
        )

    def add(self, candle: Candle) -> None:
        """Append a candle to the appropriate buffer.

        If the buffer is full the oldest candle is evicted
        automatically (deque maxlen behaviour).

        Args:
            candle: The candle to store.
        """
        key = (candle.pair, candle.timeframe)
        self._buffers[key].append(candle)

    def get_last(self, n: int, pair: str, timeframe: str) -> list[Candle]:
        """Return the last *n* candles for a given pair and timeframe.

        Args:
            n: Number of candles to retrieve.
            pair: Trading pair (e.g. "BTC/USDT").
            timeframe: Timeframe label (e.g. "5m").

        Returns:
            List of up to *n* candles, oldest first.  May be shorter
            than *n* if fewer candles are stored.
        """
        key = (pair, timeframe)
        buf = self._buffers.get(key)
        if buf is None:
            return []
        # Slice the deque from the right.
        start = max(0, len(buf) - n)
        return list(buf)[start:]

    def get_all(self, pair: str, timeframe: str) -> list[Candle]:
        """Return all stored candles for a given pair and timeframe.

        Args:
            pair: Trading pair.
            timeframe: Timeframe label.

        Returns:
            List of candles, oldest first.
        """
        key = (pair, timeframe)
        buf = self._buffers.get(key)
        if buf is None:
            return []
        return list(buf)

    def size(self, pair: str, timeframe: str) -> int:
        """Return the number of candles stored for a key."""
        key = (pair, timeframe)
        buf = self._buffers.get(key)
        return len(buf) if buf else 0

    def pairs(self) -> list[str]:
        """Return all unique pairs that have buffered data."""
        return sorted({k[0] for k in self._buffers})

    def timeframes(self, pair: str) -> list[str]:
        """Return all timeframes with data for a given pair."""
        return sorted({k[1] for k in self._buffers if k[0] == pair})

    def clear(self, pair: str | None = None, timeframe: str | None = None) -> None:
        """Clear candle data.

        Args:
            pair: If provided, only clear this pair.
            timeframe: If also provided, only clear this specific combo.
        """
        if pair is None:
            self._buffers.clear()
        elif timeframe is None:
            keys = [k for k in self._buffers if k[0] == pair]
            for k in keys:
                del self._buffers[k]
        else:
            key = (pair, timeframe)
            if key in self._buffers:
                del self._buffers[key]

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._buffers.values())
        return f"<CandleBuffer keys={len(self._buffers)} candles={total}>"
