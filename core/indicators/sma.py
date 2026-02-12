"""Simple Moving Average (SMA).

The arithmetic mean of the last *period* closing prices.  Useful as
a baseline trend filter and for building other indicators (e.g.
Bollinger Bands).

Operators supported:
    price_above  - current close > SMA value
    price_below  - current close < SMA value
    rising       - SMA is increasing
    falling      - SMA is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _get_source(candle: Candle, source: str) -> float:
    """Extract a price field from a candle by name."""
    return float(getattr(candle, source))


@register
class SMA(BaseIndicator):
    name = "Simple Moving Average"
    key = "sma"
    category = "trend"
    default_params = {"period": 20, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute SMA over a full candle history.

        Returns a state dict with:
            sma           - list of SMA values (None for first period-1)
            window        - last *period* source values (for incremental update)
            period        - the period used
            current_close - close price of the last candle
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        n = len(candles)
        sma_values: list[float | None] = [None] * n
        prices = [_get_source(c, source) for c in candles]

        if n < period:
            return {
                "sma": sma_values,
                "window": prices,
                "period": period,
                "current_close": candles[-1].close if candles else 0.0,
            }

        # Sliding window sum
        window_sum = sum(prices[:period])
        sma_values[period - 1] = window_sum / period

        for i in range(period, n):
            window_sum += prices[i] - prices[i - period]
            sma_values[i] = window_sum / period

        return {
            "sma": sma_values,
            "window": prices[-(period):] if n >= period else prices,
            "period": period,
            "current_close": candles[-1].close,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update SMA with one new candle.

        Maintains a sliding window of the last *period* source prices.
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        price = _get_source(candle, source)
        window: list[float] = state["window"]
        sma_list: list[float | None] = state["sma"]

        window.append(price)

        if len(window) > period:
            window = window[-period:]

        if len(window) == period:
            new_sma = sum(window) / period
            sma_list.append(new_sma)
        else:
            sma_list.append(None)

        state["sma"] = sma_list
        state["window"] = window
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current SMA state.

        Supported operators: price_above, price_below, rising, falling.
        """
        sma_list: list[float | None] = state.get("sma", [])
        current_close: float = state.get("current_close", 0.0)

        latest_sma = _last_valid(sma_list)
        if latest_sma is None:
            return False

        if operator == "price_above":
            return current_close > latest_sma
        elif operator == "price_below":
            return current_close < latest_sma
        elif operator == "rising":
            prev_sma = _prev_valid(sma_list)
            return prev_sma is not None and latest_sma > prev_sma
        elif operator == "falling":
            prev_sma = _prev_valid(sma_list)
            return prev_sma is not None and latest_sma < prev_sma
        else:
            raise ValueError(f"Unknown operator for SMA: {operator!r}")


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value."""
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _prev_valid(values: list[float | None]) -> float | None:
    """Return the second-to-last non-None value."""
    found = False
    for v in reversed(values):
        if v is not None:
            if found:
                return v
            found = True
    return None
