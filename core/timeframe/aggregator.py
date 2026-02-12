"""Timeframe aggregator -- builds higher-TF candles from 1-minute data.

Receives 1m candles one at a time and emits completed candles for
every higher timeframe the strategy requires (e.g. 5m, 15m, 1h).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from core.models import Candle


# Timeframe definitions: label -> duration in minutes.
TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "6h": 360,
    "8h": 480,
    "12h": 720,
    "1d": 1440,
}


class TimeframeAggregator:
    """Aggregate 1-minute candles into higher timeframes.

    Usage::

        agg = TimeframeAggregator(target_timeframes=["5m", "15m", "1h"])
        completed = agg.on_candle(candle_1m)
        for c in completed:
            # c is a completed 5m / 15m / 1h Candle
            ...
    """

    def __init__(self, target_timeframes: list[str] | None = None) -> None:
        """
        Args:
            target_timeframes: List of TF labels to aggregate to.
                Defaults to ["5m", "15m", "1h"].
        """
        self.target_timeframes = target_timeframes or ["5m", "15m", "1h"]

        # Validate requested timeframes.
        for tf in self.target_timeframes:
            if tf not in TIMEFRAME_MINUTES:
                raise ValueError(f"Unknown timeframe: {tf!r}")
            if TIMEFRAME_MINUTES[tf] <= 1:
                raise ValueError(f"Cannot aggregate to {tf!r} (must be > 1m).")

        # Buffers: (pair, timeframe) -> list of 1m candles in current period.
        self._buffers: dict[tuple[str, str], list[Candle]] = defaultdict(list)

    def on_candle(self, candle: Candle) -> list[Candle]:
        """Process a new 1-minute candle.

        Args:
            candle: A closed 1m candle.

        Returns:
            List of completed higher-TF candles (may be empty).
        """
        if candle.timeframe != "1m":
            raise ValueError(f"Expected 1m candle, got {candle.timeframe!r}.")

        completed: list[Candle] = []

        for tf in self.target_timeframes:
            result = self._aggregate(candle, tf)
            if result is not None:
                completed.append(result)

        return completed

    def _aggregate(self, candle: Candle, target_tf: str) -> Candle | None:
        """Add a 1m candle to the buffer for *target_tf* and return
        a completed candle if the period boundary has been reached.

        Args:
            candle: The incoming 1m candle.
            target_tf: Target timeframe label (e.g. "5m").

        Returns:
            Completed Candle or None if the period is still open.
        """
        tf_minutes = TIMEFRAME_MINUTES[target_tf]
        key = (candle.pair, target_tf)

        # Determine the period this candle belongs to.
        current_period_start = self._period_start(candle.timestamp, tf_minutes)

        buf = self._buffers[key]

        # If the buffer has candles from a previous period, finalize
        # that period first, then start a new one.
        if buf:
            first_period_start = self._period_start(buf[0].timestamp, tf_minutes)
            if current_period_start != first_period_start:
                # The previous period is complete -- build the candle.
                completed = self._build_candle(buf, candle.pair, target_tf, first_period_start)
                buf.clear()
                buf.append(candle)
                return completed

        # Same period or first candle: accumulate.
        buf.append(candle)

        # Check if this is the last minute of the period.
        # The period is complete when we have tf_minutes candles
        # OR the next minute would start a new period.
        next_minute = candle.timestamp + timedelta(minutes=1)
        next_period_start = self._period_start(next_minute, tf_minutes)

        if next_period_start != current_period_start:
            # This was the last 1m candle of the period.
            completed = self._build_candle(buf, candle.pair, target_tf, current_period_start)
            buf.clear()
            return completed

        return None

    @staticmethod
    def _build_candle(
        candles_1m: list[Candle],
        pair: str,
        timeframe: str,
        period_start: datetime,
    ) -> Candle:
        """Merge a list of 1m candles into a single higher-TF candle."""
        return Candle(
            timestamp=period_start,
            open=candles_1m[0].open,
            high=max(c.high for c in candles_1m),
            low=min(c.low for c in candles_1m),
            close=candles_1m[-1].close,
            volume=sum(c.volume for c in candles_1m),
            pair=pair,
            timeframe=timeframe,
            is_closed=True,
        )

    def _period_start(self, timestamp: datetime, tf_minutes: int) -> datetime:
        """Calculate the start of the period that *timestamp* belongs to.

        Aligns to UTC midnight boundaries.

        Args:
            timestamp: The candle timestamp.
            tf_minutes: Period length in minutes.

        Returns:
            Period start as datetime.
        """
        total_minutes = timestamp.hour * 60 + timestamp.minute
        period_start_minutes = (total_minutes // tf_minutes) * tf_minutes
        return timestamp.replace(
            hour=period_start_minutes // 60,
            minute=period_start_minutes % 60,
            second=0,
            microsecond=0,
        )

    def reset(self, pair: str | None = None) -> None:
        """Clear internal buffers.

        Args:
            pair: If provided, only clear buffers for this pair.
                  Otherwise clear everything.
        """
        if pair is None:
            self._buffers.clear()
        else:
            keys_to_remove = [k for k in self._buffers if k[0] == pair]
            for k in keys_to_remove:
                del self._buffers[k]
