"""Supertrend indicator.

Combines ATR-based volatility bands with trend direction.  The
supertrend line flips between support (below price in uptrend) and
resistance (above price in downtrend).  Very popular for trailing
stop placement and trend-following entries.

Operators supported:
    uptrend       - price is above the supertrend line
    downtrend     - price is below the supertrend line
    flip_up       - supertrend just flipped to uptrend
    flip_down     - supertrend just flipped to downtrend
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _true_range(candle: Candle, prev_close: float | None) -> float:
    """Calculate the True Range for a candle."""
    hl = candle.high - candle.low
    if prev_close is None:
        return hl
    hc = abs(candle.high - prev_close)
    lc = abs(candle.low - prev_close)
    return max(hl, hc, lc)


@register
class Supertrend(BaseIndicator):
    name = "Supertrend"
    key = "supertrend"
    category = "trend"
    default_params = {"period": 10, "multiplier": 3.0}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Supertrend over a full candle history.

        Returns:
            supertrend  - list of supertrend values (None before period)
            direction   - list of +1 (uptrend) / -1 (downtrend) / None
            atr         - list of ATR values (None before period)
            upper_band  - list of final upper bands
            lower_band  - list of final lower bands
            current_close - close price of the last candle
        """
        p = self.merge_params(params)
        period: int = p["period"]
        multiplier: float = p["multiplier"]
        n = len(candles)

        st_values: list[float | None] = [None] * n
        direction: list[int | None] = [None] * n
        atr_values: list[float | None] = [None] * n
        upper_bands: list[float | None] = [None] * n
        lower_bands: list[float | None] = [None] * n

        if n < period + 1:
            return self._build_state(
                st_values, direction, atr_values, upper_bands,
                lower_bands, period, multiplier, candles
            )

        # Step 1: compute True Range list
        tr_list: list[float] = [0.0] * n
        tr_list[0] = candles[0].high - candles[0].low
        for i in range(1, n):
            tr_list[i] = _true_range(candles[i], candles[i - 1].close)

        # Step 2: initial ATR (SMA of first *period* TRs, starting from index 1)
        atr_sum = sum(tr_list[1 : period + 1])
        atr = atr_sum / period
        atr_values[period] = atr

        # Step 3: iterate from period onwards
        for i in range(period, n):
            # Smoothed ATR (Wilder)
            if i > period:
                atr = (atr * (period - 1) + tr_list[i]) / period
                atr_values[i] = atr

            hl2 = (candles[i].high + candles[i].low) / 2.0
            basic_upper = hl2 + multiplier * atr
            basic_lower = hl2 - multiplier * atr

            # Final upper band: min of basic upper and previous final upper
            # (only if previous close was above previous final upper)
            if i == period:
                final_upper = basic_upper
                final_lower = basic_lower
            else:
                prev_upper = upper_bands[i - 1] if upper_bands[i - 1] is not None else basic_upper
                prev_lower = lower_bands[i - 1] if lower_bands[i - 1] is not None else basic_lower

                final_upper = (
                    min(basic_upper, prev_upper)
                    if candles[i - 1].close <= prev_upper
                    else basic_upper
                )
                final_lower = (
                    max(basic_lower, prev_lower)
                    if candles[i - 1].close >= prev_lower
                    else basic_lower
                )

            upper_bands[i] = final_upper
            lower_bands[i] = final_lower

            # Determine direction
            if i == period:
                # Initial direction based on price vs upper band
                direction[i] = 1 if candles[i].close > final_upper else -1
            else:
                prev_dir = direction[i - 1] if direction[i - 1] is not None else -1
                prev_st = st_values[i - 1]
                if prev_dir == 1:
                    # Was uptrend — stay up unless close < lower band
                    direction[i] = -1 if candles[i].close < final_lower else 1
                else:
                    # Was downtrend — stay down unless close > upper band
                    direction[i] = 1 if candles[i].close > final_upper else -1

            # Supertrend value: lower band in uptrend, upper band in downtrend
            st_values[i] = final_lower if direction[i] == 1 else final_upper

        return self._build_state(
            st_values, direction, atr_values, upper_bands,
            lower_bands, period, multiplier, candles
        )

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Supertrend with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]
        multiplier: float = p["multiplier"]

        st_list: list[float | None] = state["supertrend"]
        dir_list: list[int | None] = state["direction"]
        atr_list: list[float | None] = state["atr"]
        upper_list: list[float | None] = state["upper_band"]
        lower_list: list[float | None] = state["lower_band"]
        prev_close: float = state.get("current_close", candle.close)

        # True range
        tr = _true_range(candle, prev_close)

        # ATR update (Wilder smoothing)
        prev_atr = None
        for v in reversed(atr_list):
            if v is not None:
                prev_atr = v
                break

        if prev_atr is None:
            # Cannot compute — append None
            for lst in (st_list, dir_list, atr_list, upper_list, lower_list):
                lst.append(None)
            state["current_close"] = candle.close
            return state

        atr = (prev_atr * (period - 1) + tr) / period
        hl2 = (candle.high + candle.low) / 2.0
        basic_upper = hl2 + multiplier * atr
        basic_lower = hl2 - multiplier * atr

        prev_upper = upper_list[-1] if upper_list[-1] is not None else basic_upper
        prev_lower = lower_list[-1] if lower_list[-1] is not None else basic_lower

        final_upper = (
            min(basic_upper, prev_upper)
            if prev_close <= prev_upper
            else basic_upper
        )
        final_lower = (
            max(basic_lower, prev_lower)
            if prev_close >= prev_lower
            else basic_lower
        )

        prev_dir = dir_list[-1] if dir_list[-1] is not None else -1
        if prev_dir == 1:
            new_dir = -1 if candle.close < final_lower else 1
        else:
            new_dir = 1 if candle.close > final_upper else -1

        st_val = final_lower if new_dir == 1 else final_upper

        atr_list.append(atr)
        upper_list.append(final_upper)
        lower_list.append(final_lower)
        dir_list.append(new_dir)
        st_list.append(st_val)
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate Supertrend conditions.

        Supported: uptrend, downtrend, flip_up, flip_down.
        """
        dir_list: list[int | None] = state.get("direction", [])
        cur_dir = _last_valid(dir_list)
        if cur_dir is None:
            return False

        if operator == "uptrend":
            return cur_dir == 1
        elif operator == "downtrend":
            return cur_dir == -1
        elif operator == "flip_up":
            prev = _prev_valid_int(dir_list)
            return prev is not None and prev == -1 and cur_dir == 1
        elif operator == "flip_down":
            prev = _prev_valid_int(dir_list)
            return prev is not None and prev == 1 and cur_dir == -1
        else:
            raise ValueError(f"Unknown operator for Supertrend: {operator!r}")

    @staticmethod
    def _build_state(
        st: list, direction: list, atr: list, upper: list,
        lower: list, period: int, multiplier: float, candles: list[Candle]
    ) -> dict[str, Any]:
        return {
            "supertrend": st,
            "direction": direction,
            "atr": atr,
            "upper_band": upper,
            "lower_band": lower,
            "period": period,
            "multiplier": multiplier,
            "current_close": candles[-1].close if candles else 0.0,
        }


def _last_valid(values: list[Any]) -> Any:
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _prev_valid_int(values: list[int | None]) -> int | None:
    found = False
    for v in reversed(values):
        if v is not None:
            if found:
                return v
            found = True
    return None
