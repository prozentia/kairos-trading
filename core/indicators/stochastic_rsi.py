"""Stochastic RSI.

Applies the Stochastic Oscillator formula to RSI values instead of
price.  This makes it more sensitive than plain RSI and produces
faster signals.  Oscillates between 0 and 1 (or 0 and 100).

Calculation:
    1. Compute RSI(rsi_period)
    2. Apply Stochastic formula over stoch_period on RSI values
    3. %K = SMA(StochRSI, k_smooth)
    4. %D = SMA(%K, d_smooth)

Operators supported:
    overbought  - StochRSI %K > value (default 0.8)
    oversold    - StochRSI %K < value (default 0.2)
    cross_up    - %K crossed above %D (bullish)
    cross_down  - %K crossed below %D (bearish)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _compute_rsi_series(prices: list[float], period: int) -> list[float | None]:
    """Compute raw RSI series using Wilder smoothing."""
    n = len(prices)
    rsi_values: list[float | None] = [None] * n

    if n < period + 1:
        return rsi_values

    changes = [prices[i] - prices[i - 1] for i in range(1, n)]
    gains = [max(c, 0.0) for c in changes[:period]]
    losses = [abs(min(c, 0.0)) for c in changes[:period]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0.0:
        rsi_values[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))

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

    return rsi_values


def _sma(values: list[float], period: int) -> list[float | None]:
    """Simple Moving Average over a list of floats."""
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
class StochasticRSI(BaseIndicator):
    name = "Stochastic RSI"
    key = "stochastic_rsi"
    category = "momentum"
    default_params = {
        "rsi_period": 14,
        "stoch_period": 14,
        "k_smooth": 3,
        "d_smooth": 3,
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Stochastic RSI over a full candle history.

        Returns dict with:
            stoch_rsi  - list of raw StochRSI values (0-1)
            k          - list of smoothed %K values (0-1)
            d          - list of %D values (0-1)
            rsi_values - list of underlying RSI values
            prev_k     - previous %K for crossover detection
            prev_d     - previous %D
            current_k  - latest %K
            current_d  - latest %D
        """
        p = self.merge_params(params)
        rsi_period: int = p["rsi_period"]
        stoch_period: int = p["stoch_period"]
        k_smooth: int = p["k_smooth"]
        d_smooth: int = p["d_smooth"]

        n = len(candles)
        prices = [c.close for c in candles]

        # Step 1: compute RSI
        rsi_values = _compute_rsi_series(prices, rsi_period)

        # Step 2: apply Stochastic formula on RSI values
        # Extract non-None RSI values with their original indices
        stoch_rsi: list[float | None] = [None] * n
        rsi_clean: list[float] = []
        rsi_indices: list[int] = []
        for i, v in enumerate(rsi_values):
            if v is not None:
                rsi_clean.append(v)
                rsi_indices.append(i)

        raw_stoch_list: list[float] = []
        raw_stoch_indices: list[int] = []

        for j in range(stoch_period - 1, len(rsi_clean)):
            window = rsi_clean[j - stoch_period + 1: j + 1]
            highest_rsi = max(window)
            lowest_rsi = min(window)
            rng = highest_rsi - lowest_rsi
            if rng == 0.0:
                raw_val = 0.5  # Neutral
            else:
                raw_val = (rsi_clean[j] - lowest_rsi) / rng
            orig_idx = rsi_indices[j]
            stoch_rsi[orig_idx] = raw_val
            raw_stoch_list.append(raw_val)
            raw_stoch_indices.append(orig_idx)

        # Step 3: %K = SMA(StochRSI, k_smooth)
        k_values: list[float | None] = [None] * n
        if len(raw_stoch_list) >= k_smooth:
            k_sma = _sma(raw_stoch_list, k_smooth)
            for j, val in enumerate(k_sma):
                if val is not None:
                    k_values[raw_stoch_indices[j]] = val

        # Step 4: %D = SMA(%K, d_smooth)
        d_values: list[float | None] = [None] * n
        k_clean: list[float] = [v for v in k_values if v is not None]
        k_clean_indices: list[int] = [i for i, v in enumerate(k_values) if v is not None]
        if len(k_clean) >= d_smooth:
            d_sma = _sma(k_clean, d_smooth)
            for j, val in enumerate(d_sma):
                if val is not None:
                    d_values[k_clean_indices[j]] = val

        current_k = k_values[-1] if n > 0 else None
        current_d = d_values[-1] if n > 0 else None
        prev_k = k_values[-2] if n >= 2 else None
        prev_d = d_values[-2] if n >= 2 else None

        # Store state for incremental updates
        recent_rsi = rsi_clean[-(stoch_period):] if rsi_clean else []
        recent_raw_stoch = raw_stoch_list[-(k_smooth):] if raw_stoch_list else []
        recent_k = k_clean[-(d_smooth):] if k_clean else []

        return {
            "stoch_rsi": stoch_rsi,
            "k": k_values,
            "d": d_values,
            "rsi_values": rsi_values,
            "prev_k": prev_k,
            "prev_d": prev_d,
            "current_k": current_k,
            "current_d": current_d,
            "recent_rsi": recent_rsi,
            "recent_raw_stoch": recent_raw_stoch,
            "recent_k": recent_k,
            # RSI state for incremental RSI updates
            "_rsi_avg_gain": 0.0,
            "_rsi_avg_loss": 0.0,
            "_last_close": prices[-1] if prices else None,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update StochRSI with one new candle."""
        p = self.merge_params(params)
        rsi_period: int = p["rsi_period"]
        stoch_period: int = p["stoch_period"]
        k_smooth: int = p["k_smooth"]
        d_smooth: int = p["d_smooth"]

        recent_rsi: list[float] = state["recent_rsi"]
        recent_raw_stoch: list[float] = state["recent_raw_stoch"]
        recent_k: list[float] = state["recent_k"]
        last_close = state.get("_last_close")

        # Update RSI incrementally
        avg_gain: float = state.get("_rsi_avg_gain", 0.0)
        avg_loss: float = state.get("_rsi_avg_loss", 0.0)

        new_rsi = None
        if last_close is not None:
            change = candle.close - last_close
            gain = max(change, 0.0)
            loss = abs(min(change, 0.0))
            avg_gain = (avg_gain * (rsi_period - 1) + gain) / rsi_period
            avg_loss = (avg_loss * (rsi_period - 1) + loss) / rsi_period
            if avg_loss == 0.0:
                new_rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                new_rsi = 100.0 - (100.0 / (1.0 + rs))
            state["_rsi_avg_gain"] = avg_gain
            state["_rsi_avg_loss"] = avg_loss

        state["_last_close"] = candle.close

        if new_rsi is None:
            state["k"].append(None)
            state["d"].append(None)
            state["stoch_rsi"].append(None)
            return state

        recent_rsi.append(new_rsi)
        if len(recent_rsi) > stoch_period:
            recent_rsi.pop(0)

        # Compute raw StochRSI
        new_raw_stoch = None
        if len(recent_rsi) >= stoch_period:
            highest = max(recent_rsi)
            lowest = min(recent_rsi)
            rng = highest - lowest
            new_raw_stoch = (new_rsi - lowest) / rng if rng != 0.0 else 0.5

        state["stoch_rsi"].append(new_raw_stoch)

        # Smooth %K
        new_k = None
        if new_raw_stoch is not None:
            recent_raw_stoch.append(new_raw_stoch)
            if len(recent_raw_stoch) > k_smooth:
                recent_raw_stoch.pop(0)
            if len(recent_raw_stoch) >= k_smooth:
                new_k = sum(recent_raw_stoch) / k_smooth

        # %D
        new_d = None
        if new_k is not None:
            recent_k.append(new_k)
            if len(recent_k) > d_smooth:
                recent_k.pop(0)
            if len(recent_k) >= d_smooth:
                new_d = sum(recent_k) / d_smooth

        state["prev_k"] = state.get("current_k")
        state["prev_d"] = state.get("current_d")
        state["current_k"] = new_k
        state["current_d"] = new_d
        state["k"].append(new_k)
        state["d"].append(new_d)
        state["recent_rsi"] = recent_rsi
        state["recent_raw_stoch"] = recent_raw_stoch
        state["recent_k"] = recent_k

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate StochRSI conditions.

        Supported operators:
            overbought - %K > value (default 0.8, scale 0-1)
            oversold   - %K < value (default 0.2, scale 0-1)
            cross_up   - %K crossed above %D
            cross_down - %K crossed below %D
        """
        current_k = state.get("current_k")
        current_d = state.get("current_d")
        prev_k = state.get("prev_k")
        prev_d = state.get("prev_d")

        if operator == "overbought":
            threshold = float(value) if value is not None else 0.8
            return current_k is not None and current_k > threshold

        if operator == "oversold":
            threshold = float(value) if value is not None else 0.2
            return current_k is not None and current_k < threshold

        if operator == "cross_up":
            if None in (current_k, current_d, prev_k, prev_d):
                return False
            return prev_k <= prev_d and current_k > current_d

        if operator == "cross_down":
            if None in (current_k, current_d, prev_k, prev_d):
                return False
            return prev_k >= prev_d and current_k < current_d

        raise ValueError(f"Unknown StochasticRSI operator: {operator!r}")
