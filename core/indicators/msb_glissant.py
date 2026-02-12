"""MSB Glissant (Sliding Market Structure Break).

A custom smart-money indicator that tracks the sliding MSB level --
the most recent swing low that, when broken to the upside, signals
a shift in market structure from bearish to bullish.  Combined with
Bollinger Band proximity and Heikin-Ashi confirmation for entries.

This is the core indicator behind the original BTC Sniper Bot
strategy.

Algorithm:
    1. Detect swing highs/lows using a lookback window.
    2. Track the most recent swing high and swing low.
    3. A bullish MSB occurs when price closes above the last swing high
       (breaking bearish structure to the upside).
    4. A bearish MSB occurs when price closes below the last swing low
       (breaking bullish structure to the downside).
    5. The MSB level "slides" as new swings form.

Operators supported:
    break_up       - price just closed above MSB level (bullish break)
    break_down     - price just closed below MSB level (bearish break)
    above_msb      - price is currently above MSB
    below_msb      - price is currently below MSB
    near_bb_lower  - price is within proximity_pct of lower Bollinger Band
"""

from __future__ import annotations

import math
from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class MSBGlissant(BaseIndicator):
    name = "MSB Glissant"
    key = "msb_glissant"
    category = "special"
    default_params = {
        "swing_lookback": 5,
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "bb_proximity_pct": 0.15,
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute MSB Glissant over a full candle history.

        Returns:
            swing_highs     - list of detected swing high prices (None if not)
            swing_lows      - list of detected swing low prices (None if not)
            msb_high        - current MSB high level (last swing high)
            msb_low         - current MSB low level (last swing low)
            break_up        - True if a bullish break just occurred
            break_down      - True if a bearish break just occurred
            bb_lower        - last Bollinger lower band value
            prices          - list of close prices
        """
        p = self.merge_params(params)
        lookback: int = p["swing_lookback"]
        bb_period: int = p["bb_period"]
        bb_std_dev: float = p["bb_std_dev"]

        n = len(candles)
        swing_highs: list[float | None] = [None] * n
        swing_lows: list[float | None] = [None] * n
        prices = [c.close for c in candles]

        # Detect swing highs and lows
        for i in range(lookback, n - lookback):
            # Swing high: high[i] is higher than all highs in the window
            is_swing_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and candles[j].high >= candles[i].high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs[i] = candles[i].high

            # Swing low: low[i] is lower than all lows in the window
            is_swing_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and candles[j].low <= candles[i].low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows[i] = candles[i].low

        # Track the sliding MSB levels
        msb_high: float | None = None
        msb_low: float | None = None
        prev_msb_high: float | None = None
        prev_msb_low: float | None = None
        break_up = False
        break_down = False

        for i in range(n):
            if swing_highs[i] is not None:
                prev_msb_high = msb_high
                msb_high = swing_highs[i]
            if swing_lows[i] is not None:
                prev_msb_low = msb_low
                msb_low = swing_lows[i]

        # Check for breaks on the last candle
        if n > 0 and msb_high is not None:
            if prices[-1] > msb_high:
                # Verify previous candle was below
                if n >= 2 and prices[-2] <= msb_high:
                    break_up = True

        if n > 0 and msb_low is not None:
            if prices[-1] < msb_low:
                if n >= 2 and prices[-2] >= msb_low:
                    break_down = True

        # Compute Bollinger lower band for proximity check
        bb_lower = self._compute_bb_lower(candles, bb_period, bb_std_dev)

        return {
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "msb_high": msb_high,
            "msb_low": msb_low,
            "break_up": break_up,
            "break_down": break_down,
            "bb_lower": bb_lower,
            "prices": prices,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update MSB with one new candle."""
        p = self.merge_params(params)
        lookback: int = p["swing_lookback"]
        bb_period: int = p["bb_period"]
        bb_std_dev: float = p["bb_std_dev"]

        state["prices"].append(candle.close)
        prices = state["prices"]

        # Store candle data for swing detection
        candle_data = state.setdefault("_candle_highs", [])
        candle_lows = state.setdefault("_candle_lows", [])
        candle_data.append(candle.high)
        candle_lows.append(candle.low)

        state["swing_highs"].append(None)
        state["swing_lows"].append(None)

        n = len(prices)

        # Check if the candle at index (n - 1 - lookback) is a swing point
        check_idx = n - 1 - lookback
        if check_idx >= lookback:
            # Swing high check
            is_swing_high = True
            for j in range(check_idx - lookback, check_idx + lookback + 1):
                if j != check_idx and j < n and candle_data[j] >= candle_data[check_idx]:
                    is_swing_high = False
                    break
            if is_swing_high:
                state["swing_highs"][check_idx] = candle_data[check_idx]
                state["msb_high"] = candle_data[check_idx]

            # Swing low check
            is_swing_low = True
            for j in range(check_idx - lookback, check_idx + lookback + 1):
                if j != check_idx and j < n and candle_lows[j] <= candle_lows[check_idx]:
                    is_swing_low = False
                    break
            if is_swing_low:
                state["swing_lows"][check_idx] = candle_lows[check_idx]
                state["msb_low"] = candle_lows[check_idx]

        # Check for breaks
        msb_high = state.get("msb_high")
        msb_low = state.get("msb_low")

        state["break_up"] = False
        state["break_down"] = False

        if msb_high is not None and n >= 2:
            if prices[-1] > msb_high and prices[-2] <= msb_high:
                state["break_up"] = True

        if msb_low is not None and n >= 2:
            if prices[-1] < msb_low and prices[-2] >= msb_low:
                state["break_down"] = True

        # Update BB lower
        if n >= bb_period:
            window = prices[-bb_period:]
            sma = sum(window) / bb_period
            variance = sum((v - sma) ** 2 for v in window) / bb_period
            std = math.sqrt(max(variance, 0.0))
            state["bb_lower"] = sma - bb_std_dev * std
        else:
            state["bb_lower"] = None

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current MSB state."""
        prices = state.get("prices", [])
        price = prices[-1] if prices else None
        msb_high = state.get("msb_high")
        msb_low = state.get("msb_low")

        if operator == "break_up":
            return bool(state.get("break_up", False))

        elif operator == "break_down":
            return bool(state.get("break_down", False))

        elif operator == "above_msb":
            if price is None or msb_high is None:
                return False
            return price > msb_high

        elif operator == "below_msb":
            if price is None or msb_low is None:
                return False
            return price < msb_low

        elif operator == "near_bb_lower":
            bb_lower = state.get("bb_lower")
            proximity_pct = float(value) if value is not None else 0.15
            if price is None or bb_lower is None or bb_lower == 0:
                return False
            distance_pct = abs(price - bb_lower) / bb_lower * 100.0
            return distance_pct <= proximity_pct

        elif operator == "break_detected":
            # Either bullish or bearish break
            return bool(state.get("break_up", False)) or bool(state.get("break_down", False))

        else:
            raise ValueError(f"Unknown operator for MSB Glissant: {operator!r}")

    @staticmethod
    def _compute_bb_lower(
        candles: list[Candle], period: int, std_dev: float,
    ) -> float | None:
        """Compute the Bollinger lower band for the last candle."""
        n = len(candles)
        if n < period:
            return None

        prices = [c.close for c in candles[-period:]]
        sma = sum(prices) / period
        variance = sum((p - sma) ** 2 for p in prices) / period
        std = math.sqrt(max(variance, 0.0))
        return sma - std_dev * std
