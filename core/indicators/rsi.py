"""Relative Strength Index (RSI).

A momentum oscillator that measures the speed and magnitude of price
changes on a 0-100 scale.  Traditionally, readings above 70 indicate
overbought conditions and below 30 indicate oversold.

Uses the Wilder smoothing method (exponential moving average with
alpha = 1/period) for incremental updates.

Operators supported:
    above       - RSI > value (e.g. overbought check)
    below       - RSI < value (e.g. oversold check)
    cross_up    - RSI just crossed above value
    cross_down  - RSI just crossed below value
    rising      - RSI is increasing
    falling     - RSI is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _get_source(candle: Candle, source: str) -> float:
    """Extract the price source from a candle."""
    return getattr(candle, source)


@register
class RSI(BaseIndicator):
    name = "Relative Strength Index"
    key = "rsi"
    category = "momentum"
    default_params = {"period": 14, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute RSI over a full candle history.

        Returns dict with:
            rsi        - list of RSI values (None for warmup period)
            avg_gain   - current Wilder-smoothed average gain
            avg_loss   - current Wilder-smoothed average loss
            prev_rsi   - previous RSI value (for crossover detection)
            current_rsi - latest RSI value
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        prices = [_get_source(c, source) for c in candles]
        n = len(prices)

        rsi_values: list[float | None] = [None] * n

        if n < period + 1:
            # Not enough data to compute RSI
            return {
                "rsi": rsi_values,
                "avg_gain": 0.0,
                "avg_loss": 0.0,
                "prev_rsi": None,
                "current_rsi": None,
            }

        # Step 1: compute price changes
        changes = [prices[i] - prices[i - 1] for i in range(1, n)]

        # Step 2: first average gain/loss over the initial period (SMA seed)
        gains = [max(c, 0.0) for c in changes[:period]]
        losses = [abs(min(c, 0.0)) for c in changes[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # First RSI value at index = period
        if avg_loss == 0.0:
            rsi_values[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))

        # Step 3: Wilder smoothing for the remaining values
        for i in range(period, len(changes)):
            change = changes[i]
            gain = max(change, 0.0)
            loss = abs(min(change, 0.0))

            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0.0:
                rsi_values[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        # Find prev_rsi (second to last non-None)
        prev_rsi = None
        if n >= period + 2:
            prev_rsi = rsi_values[-2]

        return {
            "rsi": rsi_values,
            "avg_gain": avg_gain,
            "avg_loss": avg_loss,
            "prev_rsi": prev_rsi,
            "current_rsi": rsi_values[-1],
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update RSI with one new candle.

        Requires state keys: avg_gain, avg_loss, current_rsi, rsi.
        Also needs the previous candle close stored in state or passed via
        the last element of the rsi list.
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        new_price = _get_source(candle, source)
        rsi_list: list[float | None] = state["rsi"]
        avg_gain: float = state["avg_gain"]
        avg_loss: float = state["avg_loss"]

        # We need the previous close; store it in state
        prev_close: float | None = state.get("last_close")
        if prev_close is None:
            # Cannot compute change without previous close
            rsi_list.append(state.get("current_rsi"))
            state["last_close"] = new_price
            return state

        change = new_price - prev_close
        gain = max(change, 0.0)
        loss = abs(min(change, 0.0))

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0.0:
            new_rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            new_rsi = 100.0 - (100.0 / (1.0 + rs))

        state["prev_rsi"] = state.get("current_rsi")
        state["current_rsi"] = new_rsi
        state["avg_gain"] = avg_gain
        state["avg_loss"] = avg_loss
        state["last_close"] = new_price
        rsi_list.append(new_rsi)
        state["rsi"] = rsi_list

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current RSI state.

        Supported operators:
            above      - current RSI > value
            below      - current RSI < value
            cross_up   - RSI crossed above value (prev < value, current >= value)
            cross_down - RSI crossed below value (prev > value, current <= value)
            rising     - RSI is increasing
            falling    - RSI is decreasing
        """
        current = state.get("current_rsi")
        prev = state.get("prev_rsi")

        if current is None:
            return False

        if operator == "above":
            return current > float(value)

        if operator == "below":
            return current < float(value)

        if operator == "cross_up":
            if prev is None:
                return False
            return prev < float(value) and current >= float(value)

        if operator == "cross_down":
            if prev is None:
                return False
            return prev > float(value) and current <= float(value)

        if operator == "rising":
            if prev is None:
                return False
            return current > prev

        if operator == "falling":
            if prev is None:
                return False
            return current < prev

        raise ValueError(f"Unknown RSI operator: {operator!r}")
