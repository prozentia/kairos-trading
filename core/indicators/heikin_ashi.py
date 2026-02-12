"""Heikin-Ashi candle transformation.

Smooths candlestick data to make trends and reversals easier to
identify.  HA candles use modified OHLC calculations that average
current and previous values, filtering out noise.

Formulas:
    HA_Close = (Open + High + Low + Close) / 4
    HA_Open  = (prev_HA_Open + prev_HA_Close) / 2
    HA_High  = max(High, HA_Open, HA_Close)
    HA_Low   = min(Low, HA_Open, HA_Close)

Operators supported:
    is_green         - current HA candle is green (close > open)
    is_red           - current HA candle is red (close < open)
    flip_to_green    - HA just changed from red to green
    flip_to_red      - HA just changed from green to red
    consecutive_green - N consecutive green candles
    consecutive_red   - N consecutive red candles
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle, HeikinAshi


@register
class HeikinAshiIndicator(BaseIndicator):
    name = "Heikin Ashi"
    key = "heikin_ashi"
    category = "trend"
    default_params: dict[str, Any] = {}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Transform candles into Heikin-Ashi candles.

        Returns:
            ha_candles       - list of HeikinAshi objects
            is_green         - list of bool (True if green)
            consecutive_green - current count of consecutive green
            consecutive_red   - current count of consecutive red
        """
        n = len(candles)
        ha_candles: list[HeikinAshi] = []
        is_green_list: list[bool] = []

        if n == 0:
            return self._build_state(ha_candles, is_green_list, 0, 0)

        # First HA candle
        first = candles[0]
        ha_close = (first.open + first.high + first.low + first.close) / 4.0
        ha_open = (first.open + first.close) / 2.0
        ha_high = max(first.high, ha_open, ha_close)
        ha_low = min(first.low, ha_open, ha_close)
        green = ha_close > ha_open

        ha = HeikinAshi(
            timestamp=first.timestamp,
            open=ha_open,
            high=ha_high,
            low=ha_low,
            close=ha_close,
            is_green=green,
            pair=first.pair,
            timeframe=first.timeframe,
        )
        ha_candles.append(ha)
        is_green_list.append(green)

        # Remaining candles
        for i in range(1, n):
            c = candles[i]
            prev_ha = ha_candles[-1]

            ha_close = (c.open + c.high + c.low + c.close) / 4.0
            ha_open = (prev_ha.open + prev_ha.close) / 2.0
            ha_high = max(c.high, ha_open, ha_close)
            ha_low = min(c.low, ha_open, ha_close)
            green = ha_close > ha_open

            ha = HeikinAshi(
                timestamp=c.timestamp,
                open=ha_open,
                high=ha_high,
                low=ha_low,
                close=ha_close,
                is_green=green,
                pair=c.pair,
                timeframe=c.timeframe,
            )
            ha_candles.append(ha)
            is_green_list.append(green)

        # Count consecutive green/red at the end
        consec_green, consec_red = _count_consecutive(is_green_list)

        return self._build_state(ha_candles, is_green_list, consec_green, consec_red)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally compute one new HA candle."""
        ha_candles: list[HeikinAshi] = state["ha_candles"]
        is_green_list: list[bool] = state["is_green"]

        ha_close = (candle.open + candle.high + candle.low + candle.close) / 4.0

        if ha_candles:
            prev_ha = ha_candles[-1]
            ha_open = (prev_ha.open + prev_ha.close) / 2.0
        else:
            ha_open = (candle.open + candle.close) / 2.0

        ha_high = max(candle.high, ha_open, ha_close)
        ha_low = min(candle.low, ha_open, ha_close)
        green = ha_close > ha_open

        ha = HeikinAshi(
            timestamp=candle.timestamp,
            open=ha_open,
            high=ha_high,
            low=ha_low,
            close=ha_close,
            is_green=green,
            pair=candle.pair,
            timeframe=candle.timeframe,
        )
        ha_candles.append(ha)
        is_green_list.append(green)

        consec_green, consec_red = _count_consecutive(is_green_list)
        state["consecutive_green"] = consec_green
        state["consecutive_red"] = consec_red

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current Heikin-Ashi state."""
        is_green_list: list[bool] = state.get("is_green", [])

        if not is_green_list:
            return False

        current_green = is_green_list[-1]

        if operator == "is_green":
            return current_green

        elif operator == "is_red":
            return not current_green

        elif operator == "flip_to_green":
            if len(is_green_list) < 2:
                return False
            return current_green and not is_green_list[-2]

        elif operator == "flip_to_red":
            if len(is_green_list) < 2:
                return False
            return not current_green and is_green_list[-2]

        elif operator == "consecutive_green":
            threshold = int(value) if value is not None else 3
            return state.get("consecutive_green", 0) >= threshold

        elif operator == "consecutive_red":
            threshold = int(value) if value is not None else 3
            return state.get("consecutive_red", 0) >= threshold

        else:
            raise ValueError(f"Unknown operator for Heikin Ashi: {operator!r}")

    @staticmethod
    def _build_state(
        ha_candles: list[HeikinAshi],
        is_green: list[bool],
        consec_green: int,
        consec_red: int,
    ) -> dict[str, Any]:
        return {
            "ha_candles": ha_candles,
            "is_green": is_green,
            "consecutive_green": consec_green,
            "consecutive_red": consec_red,
        }


def _count_consecutive(is_green_list: list[bool]) -> tuple[int, int]:
    """Count consecutive green/red candles from the end.

    Returns (consecutive_green, consecutive_red).
    """
    if not is_green_list:
        return 0, 0

    last = is_green_list[-1]
    count = 0
    for val in reversed(is_green_list):
        if val == last:
            count += 1
        else:
            break

    if last:
        return count, 0
    else:
        return 0, count
