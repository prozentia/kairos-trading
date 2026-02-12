"""Donchian Channel.

Plots the highest high and lowest low over the last *period* candles.
The middle line is the average of the upper and lower bands.  Used in
breakout strategies (e.g. Turtle Trading) and as a volatility measure.

Operators supported:
    breakout_up    - price closed above the upper band
    breakout_down  - price closed below the lower band
    inside         - price is between the bands
    squeeze        - channel width is narrowing (low volatility)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class DonchianChannel(BaseIndicator):
    name = "Donchian Channel"
    key = "donchian"
    category = "trend"
    default_params = {"period": 20}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Donchian Channel over a full candle history.

        Returns:
            upper    - list of highest highs over period (None before period)
            lower    - list of lowest lows over period
            middle   - list of (upper + lower) / 2
            width    - list of (upper - lower)
            period   - period used
            current_close - close of last candle
            highs    - last *period* highs (for incremental update)
            lows     - last *period* lows (for incremental update)
        """
        p = self.merge_params(params)
        period: int = p["period"]
        n = len(candles)

        upper: list[float | None] = [None] * n
        lower: list[float | None] = [None] * n
        middle: list[float | None] = [None] * n
        width: list[float | None] = [None] * n

        if n < period:
            return self._build_state(
                upper, lower, middle, width, period, candles
            )

        for i in range(period - 1, n):
            window_start = i - period + 1
            h = max(candles[j].high for j in range(window_start, i + 1))
            lo = min(candles[j].low for j in range(window_start, i + 1))
            upper[i] = h
            lower[i] = lo
            middle[i] = (h + lo) / 2.0
            width[i] = h - lo

        return self._build_state(upper, lower, middle, width, period, candles)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Donchian Channel with one new candle.

        Maintains a deque-like window of recent highs and lows.
        """
        p = self.merge_params(params)
        period: int = p["period"]

        upper_list: list[float | None] = state["upper"]
        lower_list: list[float | None] = state["lower"]
        middle_list: list[float | None] = state["middle"]
        width_list: list[float | None] = state["width"]
        highs: list[float] = state.get("_highs", [])
        lows: list[float] = state.get("_lows", [])

        highs.append(candle.high)
        lows.append(candle.low)
        if len(highs) > period:
            highs = highs[-period:]
            lows = lows[-period:]

        if len(highs) >= period:
            h = max(highs)
            lo = min(lows)
            upper_list.append(h)
            lower_list.append(lo)
            middle_list.append((h + lo) / 2.0)
            width_list.append(h - lo)
        else:
            upper_list.append(None)
            lower_list.append(None)
            middle_list.append(None)
            width_list.append(None)

        state["_highs"] = highs
        state["_lows"] = lows
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate Donchian Channel conditions.

        Supported: breakout_up, breakout_down, inside, squeeze.
        """
        upper_list: list[float | None] = state.get("upper", [])
        lower_list: list[float | None] = state.get("lower", [])
        width_list: list[float | None] = state.get("width", [])
        current_close: float = state.get("current_close", 0.0)

        latest_upper = _last_valid(upper_list)
        latest_lower = _last_valid(lower_list)

        if latest_upper is None or latest_lower is None:
            return False

        if operator == "breakout_up":
            return current_close >= latest_upper
        elif operator == "breakout_down":
            return current_close <= latest_lower
        elif operator == "inside":
            return latest_lower < current_close < latest_upper
        elif operator == "squeeze":
            # Channel is narrowing: compare latest width to previous width
            latest_w = _last_valid(width_list)
            prev_w = _prev_valid(width_list)
            if latest_w is None or prev_w is None:
                return False
            return latest_w < prev_w
        else:
            raise ValueError(f"Unknown operator for Donchian: {operator!r}")

    @staticmethod
    def _build_state(
        upper: list, lower: list, middle: list, width: list,
        period: int, candles: list[Candle]
    ) -> dict[str, Any]:
        # Build highs/lows window for incremental updates
        n = len(candles)
        if n >= period:
            highs = [c.high for c in candles[-period:]]
            lows = [c.low for c in candles[-period:]]
        else:
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]
        return {
            "upper": upper,
            "lower": lower,
            "middle": middle,
            "width": width,
            "period": period,
            "_highs": highs,
            "_lows": lows,
            "current_close": candles[-1].close if candles else 0.0,
        }


def _last_valid(values: list[Any]) -> Any:
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _prev_valid(values: list[Any]) -> Any:
    found = False
    for v in reversed(values):
        if v is not None:
            if found:
                return v
            found = True
    return None
