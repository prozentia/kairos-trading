"""Keltner Channel.

An EMA-based envelope indicator using ATR for band width instead of
standard deviation (unlike Bollinger Bands).  Useful for detecting
breakouts and volatility squeezes, especially when combined with
Bollinger Bands (the "TTM Squeeze" setup).

Operators supported:
    touch_upper    - price >= upper channel
    touch_lower    - price <= lower channel
    inside         - price is between the channels
    breakout_up    - price just broke above upper channel
    breakout_down  - price just broke below lower channel
    squeeze_with_bb - Bollinger inside Keltner (volatility squeeze)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _true_range(high: float, low: float, prev_close: float) -> float:
    """Compute the true range for a single bar."""
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close),
    )


@register
class KeltnerChannel(BaseIndicator):
    name = "Keltner Channel"
    key = "keltner"
    category = "volatility"
    default_params = {"ema_period": 20, "atr_period": 10, "multiplier": 1.5}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Keltner Channel over a full candle history.

        Returns:
            upper   - list of upper channel values
            middle  - list of EMA values (middle line)
            lower   - list of lower channel values
            atr     - list of ATR values
            prices  - list of close prices
        """
        p = self.merge_params(params)
        ema_period: int = p["ema_period"]
        atr_period: int = p["atr_period"]
        multiplier: float = p["multiplier"]

        n = len(candles)
        upper: list[float | None] = [None] * n
        middle: list[float | None] = [None] * n
        lower: list[float | None] = [None] * n
        atr_values: list[float | None] = [None] * n
        prices = [c.close for c in candles]

        if n == 0:
            return self._build_state(upper, middle, lower, atr_values, prices)

        # --- Compute EMA ---
        ema_values: list[float | None] = [None] * n
        if n >= ema_period:
            # Seed with SMA
            seed = sum(prices[:ema_period]) / ema_period
            ema_values[ema_period - 1] = seed
            mult = 2.0 / (ema_period + 1)
            prev = seed
            for i in range(ema_period, n):
                val = (prices[i] - prev) * mult + prev
                ema_values[i] = val
                prev = val

        # --- Compute ATR (Wilder smoothing) ---
        tr_values: list[float] = [0.0] * n
        tr_values[0] = candles[0].high - candles[0].low
        for i in range(1, n):
            tr_values[i] = _true_range(
                candles[i].high, candles[i].low, candles[i - 1].close
            )

        if n > atr_period:
            atr_seed = sum(tr_values[1 : atr_period + 1]) / atr_period
            atr_values[atr_period] = atr_seed
            prev_atr = atr_seed
            for i in range(atr_period + 1, n):
                current_atr = (prev_atr * (atr_period - 1) + tr_values[i]) / atr_period
                atr_values[i] = current_atr
                prev_atr = current_atr

        # --- Compute channels ---
        for i in range(n):
            if ema_values[i] is not None and atr_values[i] is not None:
                middle[i] = ema_values[i]
                upper[i] = ema_values[i] + multiplier * atr_values[i]
                lower[i] = ema_values[i] - multiplier * atr_values[i]

        return self._build_state(upper, middle, lower, atr_values, prices)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Keltner Channel with one new candle."""
        p = self.merge_params(params)
        ema_period: int = p["ema_period"]
        atr_period: int = p["atr_period"]
        multiplier: float = p["multiplier"]

        price = candle.close
        state["prices"].append(price)

        # Update EMA
        prev_ema = _last_valid(state["middle"])
        if prev_ema is not None:
            mult = 2.0 / (ema_period + 1)
            new_ema = (price - prev_ema) * mult + prev_ema
        else:
            # Check if we have enough prices to seed
            prices = state["prices"]
            if len(prices) >= ema_period:
                new_ema = sum(prices[-ema_period:]) / ema_period
            else:
                state["upper"].append(None)
                state["middle"].append(None)
                state["lower"].append(None)
                state["atr"].append(None)
                return state

        # Update ATR
        prev_close = state.get("_prev_close", candle.open)
        tr = _true_range(candle.high, candle.low, prev_close)

        prev_atr = _last_valid(state["atr"])
        if prev_atr is not None:
            new_atr = (prev_atr * (atr_period - 1) + tr) / atr_period
        else:
            new_atr = tr  # Fallback

        state["middle"].append(new_ema)
        state["atr"].append(new_atr)
        state["upper"].append(new_ema + multiplier * new_atr)
        state["lower"].append(new_ema - multiplier * new_atr)
        state["_prev_close"] = candle.close

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current Keltner state."""
        upper = _last_valid(state.get("upper", []))
        lower = _last_valid(state.get("lower", []))
        prices = state.get("prices", [])
        price = prices[-1] if prices else None

        if operator == "touch_upper":
            if price is None or upper is None:
                return False
            return price >= upper

        elif operator == "touch_lower":
            if price is None or lower is None:
                return False
            return price <= lower

        elif operator == "inside":
            if price is None or upper is None or lower is None:
                return False
            return lower < price < upper

        elif operator == "breakout_up":
            if price is None or upper is None or len(prices) < 2:
                return False
            prev_upper_list = state.get("upper", [])
            if len(prev_upper_list) < 2:
                return False
            prev_upper = prev_upper_list[-2]
            prev_price = prices[-2]
            if prev_upper is None:
                return False
            return price >= upper and prev_price < prev_upper

        elif operator == "breakout_down":
            if price is None or lower is None or len(prices) < 2:
                return False
            prev_lower_list = state.get("lower", [])
            if len(prev_lower_list) < 2:
                return False
            prev_lower = prev_lower_list[-2]
            prev_price = prices[-2]
            if prev_lower is None:
                return False
            return price <= lower and prev_price > prev_lower

        elif operator == "squeeze_with_bb":
            # Value should be a dict with bb_upper and bb_lower keys,
            # or simply check if Bollinger bands are inside Keltner
            if upper is None or lower is None:
                return False
            if isinstance(value, dict):
                bb_upper = value.get("bb_upper")
                bb_lower = value.get("bb_lower")
                if bb_upper is None or bb_lower is None:
                    return False
                return bb_lower > lower and bb_upper < upper
            return False

        else:
            raise ValueError(f"Unknown operator for Keltner: {operator!r}")

    @staticmethod
    def _build_state(
        upper: list, middle: list, lower: list,
        atr: list, prices: list,
    ) -> dict[str, Any]:
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "atr": atr,
            "prices": prices,
        }


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value."""
    for v in reversed(values):
        if v is not None:
            return v
    return None
