"""Stochastic Oscillator.

Compares a closing price to a range of prices over a given period.
The %K line shows where the close sits within the recent high-low
range, and %D is a smoothed version.  Used to spot overbought/oversold
conditions and potential reversals.

Calculation:
    Raw %K = (close - lowest_low) / (highest_high - lowest_low) * 100
    %K (slow) = SMA(Raw %K, smooth)
    %D = SMA(%K, d_period)

Operators supported:
    overbought   - %K > value (default 80)
    oversold     - %K < value (default 20)
    cross_up     - %K crossed above %D (bullish)
    cross_down   - %K crossed below %D (bearish)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _sma(values: list[float], period: int) -> list[float | None]:
    """Compute Simple Moving Average over a list of values."""
    n = len(values)
    result: list[float | None] = [None] * n
    if n < period:
        return result
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for i in range(period, n):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period
    return result


@register
class Stochastic(BaseIndicator):
    name = "Stochastic Oscillator"
    key = "stochastic"
    category = "momentum"
    default_params = {"k_period": 14, "d_period": 3, "smooth": 3}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Stochastic Oscillator over a full candle history.

        Returns dict with:
            k         - list of %K values (smoothed)
            d         - list of %D values (SMA of %K)
            raw_k     - list of raw %K values (unsmoothed)
            prev_k    - previous %K value
            prev_d    - previous %D value
            current_k - latest %K value
            current_d - latest %D value
        """
        p = self.merge_params(params)
        k_period: int = p["k_period"]
        d_period: int = p["d_period"]
        smooth: int = p["smooth"]

        n = len(candles)
        raw_k_values: list[float | None] = [None] * n

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        # Step 1: compute raw %K
        raw_k_list: list[float] = []
        for i in range(k_period - 1, n):
            highest = max(highs[i - k_period + 1: i + 1])
            lowest = min(lows[i - k_period + 1: i + 1])
            rng = highest - lowest
            if rng == 0.0:
                raw_k = 50.0  # Neutral when no range
            else:
                raw_k = ((closes[i] - lowest) / rng) * 100.0
            raw_k_values[i] = raw_k
            raw_k_list.append(raw_k)

        # Step 2: smooth raw %K with SMA to get slow %K
        k_values: list[float | None] = [None] * n
        if len(raw_k_list) >= smooth:
            smoothed = _sma(raw_k_list, smooth)
            offset = k_period - 1
            for j, val in enumerate(smoothed):
                if val is not None:
                    k_values[offset + j] = val

        # Step 3: %D = SMA of %K
        d_values: list[float | None] = [None] * n
        k_for_d: list[float] = [v for v in k_values if v is not None]
        if len(k_for_d) >= d_period:
            d_sma = _sma(k_for_d, d_period)
            # Map back to original indices
            k_indices = [i for i, v in enumerate(k_values) if v is not None]
            for j, d_val in enumerate(d_sma):
                if d_val is not None:
                    d_values[k_indices[j]] = d_val

        current_k = k_values[-1] if n > 0 else None
        current_d = d_values[-1] if n > 0 else None
        prev_k = k_values[-2] if n >= 2 else None
        prev_d = d_values[-2] if n >= 2 else None

        # Store recent raw_k and k values for incremental updates
        recent_highs = highs[-(k_period):] if n >= k_period else highs[:]
        recent_lows = lows[-(k_period):] if n >= k_period else lows[:]
        recent_raw_k = [v for v in raw_k_list[-(smooth):]] if raw_k_list else []
        recent_k = [v for v in k_for_d[-(d_period):]] if k_for_d else []

        return {
            "k": k_values,
            "d": d_values,
            "raw_k": raw_k_values,
            "prev_k": prev_k,
            "prev_d": prev_d,
            "current_k": current_k,
            "current_d": current_d,
            "recent_highs": recent_highs,
            "recent_lows": recent_lows,
            "recent_raw_k": recent_raw_k,
            "recent_k": recent_k,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Stochastic with one new candle."""
        p = self.merge_params(params)
        k_period: int = p["k_period"]
        d_period: int = p["d_period"]
        smooth: int = p["smooth"]

        recent_highs: list[float] = state["recent_highs"]
        recent_lows: list[float] = state["recent_lows"]
        recent_raw_k: list[float] = state["recent_raw_k"]
        recent_k: list[float] = state["recent_k"]

        # Update rolling highs/lows
        recent_highs.append(candle.high)
        if len(recent_highs) > k_period:
            recent_highs.pop(0)
        recent_lows.append(candle.low)
        if len(recent_lows) > k_period:
            recent_lows.pop(0)

        # Compute new raw %K
        if len(recent_highs) >= k_period:
            highest = max(recent_highs)
            lowest = min(recent_lows)
            rng = highest - lowest
            raw_k = ((candle.close - lowest) / rng) * 100.0 if rng != 0.0 else 50.0

            recent_raw_k.append(raw_k)
            if len(recent_raw_k) > smooth:
                recent_raw_k.pop(0)

            # Smooth %K
            new_k = None
            if len(recent_raw_k) >= smooth:
                new_k = sum(recent_raw_k) / smooth

            # %D
            new_d = None
            if new_k is not None:
                recent_k.append(new_k)
                if len(recent_k) > d_period:
                    recent_k.pop(0)
                if len(recent_k) >= d_period:
                    new_d = sum(recent_k) / d_period

            state["prev_k"] = state.get("current_k")
            state["prev_d"] = state.get("current_d")
            state["current_k"] = new_k
            state["current_d"] = new_d

            state["k"].append(new_k)
            state["d"].append(new_d)
            state["raw_k"].append(raw_k)
        else:
            state["k"].append(None)
            state["d"].append(None)
            state["raw_k"].append(None)

        state["recent_highs"] = recent_highs
        state["recent_lows"] = recent_lows
        state["recent_raw_k"] = recent_raw_k
        state["recent_k"] = recent_k

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate Stochastic conditions.

        Supported operators:
            overbought - %K > value (default 80)
            oversold   - %K < value (default 20)
            cross_up   - %K crossed above %D
            cross_down - %K crossed below %D
        """
        current_k = state.get("current_k")
        current_d = state.get("current_d")
        prev_k = state.get("prev_k")
        prev_d = state.get("prev_d")

        if operator == "overbought":
            threshold = float(value) if value is not None else 80.0
            return current_k is not None and current_k > threshold

        if operator == "oversold":
            threshold = float(value) if value is not None else 20.0
            return current_k is not None and current_k < threshold

        if operator == "cross_up":
            if None in (current_k, current_d, prev_k, prev_d):
                return False
            return prev_k <= prev_d and current_k > current_d

        if operator == "cross_down":
            if None in (current_k, current_d, prev_k, prev_d):
                return False
            return prev_k >= prev_d and current_k < current_d

        raise ValueError(f"Unknown Stochastic operator: {operator!r}")
