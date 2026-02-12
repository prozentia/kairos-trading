"""Exponential Moving Average (EMA).

Gives more weight to recent prices, making it more responsive to new
information than a Simple Moving Average.  Commonly used to identify
trend direction and dynamic support/resistance levels.

Operators supported:
    price_above  - current close > EMA value
    price_below  - current close < EMA value
    rising       - EMA is increasing
    falling      - EMA is decreasing
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
class EMA(BaseIndicator):
    name = "Exponential Moving Average"
    key = "ema"
    category = "trend"
    default_params = {"period": 20, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute EMA over a full candle history.

        Returns a state dict with:
            ema        - list of EMA values (None for first period-1 entries)
            period     - the period used
            current_close - close price of the last candle
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        n = len(candles)
        ema_values: list[float | None] = [None] * n

        if n < period:
            return {
                "ema": ema_values,
                "period": period,
                "current_close": candles[-1].close if candles else 0.0,
            }

        # Seed: SMA of first *period* values
        seed_sum = sum(_get_source(candles[i], source) for i in range(period))
        sma_seed = seed_sum / period
        ema_values[period - 1] = sma_seed

        multiplier = 2.0 / (period + 1)

        # Compute EMA for remaining candles
        prev_ema = sma_seed
        for i in range(period, n):
            price = _get_source(candles[i], source)
            current_ema = (price - prev_ema) * multiplier + prev_ema
            ema_values[i] = current_ema
            prev_ema = current_ema

        return {
            "ema": ema_values,
            "period": period,
            "current_close": candles[-1].close,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update EMA with one new candle.

        Appends a new EMA value to the list and updates current_close.
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        ema_list: list[float | None] = state["ema"]
        multiplier = 2.0 / (period + 1)

        price = _get_source(candle, source)

        # Find the last valid EMA value
        prev_ema: float | None = None
        for v in reversed(ema_list):
            if v is not None:
                prev_ema = v
                break

        if prev_ema is None:
            # Not enough data yet — try to compute SMA if we now have enough values
            non_none_count = sum(1 for v in ema_list if v is None)
            # We cannot compute yet, just append None
            ema_list.append(None)
        else:
            new_ema = (price - prev_ema) * multiplier + prev_ema
            ema_list.append(new_ema)

        state["ema"] = ema_list
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current EMA state.

        Supported operators: price_above, price_below, rising, falling.
        """
        ema_list: list[float | None] = state.get("ema", [])
        current_close: float = state.get("current_close", 0.0)

        # Get the latest EMA value
        latest_ema: float | None = None
        for v in reversed(ema_list):
            if v is not None:
                latest_ema = v
                break

        if latest_ema is None:
            return False

        if operator == "price_above":
            return current_close > latest_ema
        elif operator == "price_below":
            return current_close < latest_ema
        elif operator == "rising":
            # Compare last two valid EMA values
            prev_ema = _find_prev_valid(ema_list)
            if prev_ema is None:
                return False
            return latest_ema > prev_ema
        elif operator == "falling":
            prev_ema = _find_prev_valid(ema_list)
            if prev_ema is None:
                return False
            return latest_ema < prev_ema
        else:
            raise ValueError(f"Unknown operator for EMA: {operator!r}")


def _find_prev_valid(values: list[float | None]) -> float | None:
    """Return the second-to-last non-None value in a list."""
    found_last = False
    for v in reversed(values):
        if v is not None:
            if found_last:
                return v
            found_last = True
    return None
