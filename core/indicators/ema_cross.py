"""EMA Crossover detector.

Tracks two EMAs (fast and slow) and detects golden crosses (fast
crosses above slow) and death crosses (fast crosses below slow).
A classic trend-following entry/exit signal.

Operators supported:
    golden_cross  - fast EMA just crossed above slow EMA
    death_cross   - fast EMA just crossed below slow EMA
    bullish       - fast EMA > slow EMA (trend confirmation)
    bearish       - fast EMA < slow EMA
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _get_source(candle: Candle, source: str) -> float:
    """Extract a price field from a candle by name."""
    return float(getattr(candle, source))


def _compute_ema_series(prices: list[float], period: int) -> list[float | None]:
    """Compute a full EMA series from a list of prices.

    Returns a list of the same length; entries before the seed are None.
    """
    n = len(prices)
    result: list[float | None] = [None] * n
    if n < period:
        return result

    # Seed with SMA of first *period* values
    seed = sum(prices[:period]) / period
    result[period - 1] = seed

    multiplier = 2.0 / (period + 1)
    prev = seed
    for i in range(period, n):
        cur = (prices[i] - prev) * multiplier + prev
        result[i] = cur
        prev = cur
    return result


@register
class EMACross(BaseIndicator):
    name = "EMA Crossover"
    key = "ema_cross"
    category = "trend"
    default_params = {"fast_period": 9, "slow_period": 21, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute fast and slow EMA over the full candle history.

        Returns:
            fast_ema      - list of fast EMA values
            slow_ema      - list of slow EMA values
            fast_period   - period used for fast EMA
            slow_period   - period used for slow EMA
            current_close - close of the last candle
        """
        p = self.merge_params(params)
        fast_period: int = p["fast_period"]
        slow_period: int = p["slow_period"]
        source: str = p["source"]

        prices = [_get_source(c, source) for c in candles]
        fast_ema = _compute_ema_series(prices, fast_period)
        slow_ema = _compute_ema_series(prices, slow_period)

        return {
            "fast_ema": fast_ema,
            "slow_ema": slow_ema,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "current_close": candles[-1].close if candles else 0.0,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update both EMAs with one new candle."""
        p = self.merge_params(params)
        fast_period: int = p["fast_period"]
        slow_period: int = p["slow_period"]
        source: str = p["source"]

        price = _get_source(candle, source)
        fast_list: list[float | None] = state["fast_ema"]
        slow_list: list[float | None] = state["slow_ema"]

        fast_list.append(_update_single(fast_list, price, fast_period))
        slow_list.append(_update_single(slow_list, price, slow_period))

        state["fast_ema"] = fast_list
        state["slow_ema"] = slow_list
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate crossover conditions.

        Supported operators:
            golden_cross  - fast just crossed above slow
            death_cross   - fast just crossed below slow
            bullish       - fast > slow
            bearish       - fast < slow
        """
        fast_list: list[float | None] = state.get("fast_ema", [])
        slow_list: list[float | None] = state.get("slow_ema", [])

        # Get last two pairs of valid values
        cur = _latest_pair(fast_list, slow_list)
        if cur is None:
            return False
        fast_cur, slow_cur, idx = cur

        if operator == "bullish":
            return fast_cur > slow_cur
        elif operator == "bearish":
            return fast_cur < slow_cur
        elif operator == "golden_cross":
            prev = _prev_pair(fast_list, slow_list, idx)
            if prev is None:
                return False
            fast_prev, slow_prev = prev
            return fast_prev <= slow_prev and fast_cur > slow_cur
        elif operator == "death_cross":
            prev = _prev_pair(fast_list, slow_list, idx)
            if prev is None:
                return False
            fast_prev, slow_prev = prev
            return fast_prev >= slow_prev and fast_cur < slow_cur
        else:
            raise ValueError(f"Unknown operator for EMA Cross: {operator!r}")


def _update_single(
    ema_list: list[float | None], price: float, period: int
) -> float | None:
    """Compute the next EMA value from the list and a new price."""
    prev = None
    for v in reversed(ema_list):
        if v is not None:
            prev = v
            break
    if prev is None:
        return None
    multiplier = 2.0 / (period + 1)
    return (price - prev) * multiplier + prev


def _latest_pair(
    fast: list[float | None], slow: list[float | None]
) -> tuple[float, float, int] | None:
    """Return the latest index where both fast and slow are valid."""
    n = min(len(fast), len(slow))
    for i in range(n - 1, -1, -1):
        if fast[i] is not None and slow[i] is not None:
            return fast[i], slow[i], i
    return None


def _prev_pair(
    fast: list[float | None], slow: list[float | None], before: int
) -> tuple[float, float] | None:
    """Return the pair just before *before* where both are valid."""
    for i in range(before - 1, -1, -1):
        if fast[i] is not None and slow[i] is not None:
            return fast[i], slow[i]
    return None
