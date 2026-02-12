"""Parabolic SAR (Stop and Reverse).

A trend-following indicator that places dots above or below price to
signal potential reversals.  The dots accelerate towards price as the
trend continues, making it useful as a trailing stop mechanism.

Operators supported:
    bullish     - SAR dots are below price (uptrend)
    bearish     - SAR dots are above price (downtrend)
    flip_up     - SAR just flipped from above to below price
    flip_down   - SAR just flipped from below to above price
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class ParabolicSAR(BaseIndicator):
    name = "Parabolic SAR"
    key = "parabolic_sar"
    category = "trend"
    default_params = {"af_start": 0.02, "af_step": 0.02, "af_max": 0.2}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Parabolic SAR over a full candle history.

        Returns:
            sar        - list of SAR values
            direction  - list of +1 (bullish/rising) / -1 (bearish/falling)
            af_start, af_step, af_max - params used
            current_close - close of last candle
        """
        p = self.merge_params(params)
        af_start: float = p["af_start"]
        af_step: float = p["af_step"]
        af_max: float = p["af_max"]

        n = len(candles)
        sar_values: list[float | None] = [None] * n
        dir_values: list[int | None] = [None] * n

        if n < 2:
            return self._build_state(
                sar_values, dir_values, af_start, af_step, af_max, candles
            )

        # Initial direction: use first two candles
        if candles[1].close >= candles[0].close:
            direction = 1  # bullish
            sar = candles[0].low
            ep = candles[1].high  # extreme point
        else:
            direction = -1  # bearish
            sar = candles[0].high
            ep = candles[1].low

        af = af_start
        sar_values[0] = sar
        dir_values[0] = direction
        sar_values[1] = sar
        dir_values[1] = direction

        for i in range(2, n):
            # Compute next SAR
            prev_sar = sar
            sar = prev_sar + af * (ep - prev_sar)

            # Make sure SAR does not penetrate prior candles
            if direction == 1:
                sar = min(sar, candles[i - 1].low, candles[i - 2].low)
            else:
                sar = max(sar, candles[i - 1].high, candles[i - 2].high)

            # Check for reversal
            if direction == 1 and candles[i].low < sar:
                # Flip to bearish
                direction = -1
                sar = ep  # SAR becomes the extreme point
                ep = candles[i].low
                af = af_start
            elif direction == -1 and candles[i].high > sar:
                # Flip to bullish
                direction = 1
                sar = ep
                ep = candles[i].high
                af = af_start
            else:
                # Continue trend — update extreme point
                if direction == 1:
                    if candles[i].high > ep:
                        ep = candles[i].high
                        af = min(af + af_step, af_max)
                else:
                    if candles[i].low < ep:
                        ep = candles[i].low
                        af = min(af + af_step, af_max)

            sar_values[i] = sar
            dir_values[i] = direction

        return self._build_state(
            sar_values, dir_values, af_start, af_step, af_max, candles,
            _af=af, _ep=ep
        )

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Parabolic SAR with one new candle."""
        p = self.merge_params(params)
        af_start: float = p["af_start"]
        af_step: float = p["af_step"]
        af_max: float = p["af_max"]

        sar_list: list[float | None] = state["sar"]
        dir_list: list[int | None] = state["direction"]
        af: float = state.get("_af", af_start)
        ep: float = state.get("_ep", candle.high)

        prev_sar = sar_list[-1]
        prev_dir = dir_list[-1]
        prev2_candle_high = state.get("_prev_high", candle.high)
        prev2_candle_low = state.get("_prev_low", candle.low)

        if prev_sar is None or prev_dir is None:
            sar_list.append(None)
            dir_list.append(None)
            state["current_close"] = candle.close
            return state

        direction = prev_dir
        sar = prev_sar + af * (ep - prev_sar)

        # Constrain SAR
        if direction == 1:
            sar = min(sar, prev2_candle_low)
        else:
            sar = max(sar, prev2_candle_high)

        # Check reversal
        if direction == 1 and candle.low < sar:
            direction = -1
            sar = ep
            ep = candle.low
            af = af_start
        elif direction == -1 and candle.high > sar:
            direction = 1
            sar = ep
            ep = candle.high
            af = af_start
        else:
            if direction == 1 and candle.high > ep:
                ep = candle.high
                af = min(af + af_step, af_max)
            elif direction == -1 and candle.low < ep:
                ep = candle.low
                af = min(af + af_step, af_max)

        sar_list.append(sar)
        dir_list.append(direction)
        state["_af"] = af
        state["_ep"] = ep
        state["_prev_high"] = candle.high
        state["_prev_low"] = candle.low
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate Parabolic SAR conditions.

        Supported: bullish, bearish, flip_up, flip_down.
        """
        dir_list: list[int | None] = state.get("direction", [])

        cur_dir = _last_valid(dir_list)
        if cur_dir is None:
            return False

        if operator == "bullish":
            return cur_dir == 1
        elif operator == "bearish":
            return cur_dir == -1
        elif operator == "flip_up":
            prev = _prev_valid(dir_list)
            return prev is not None and prev == -1 and cur_dir == 1
        elif operator == "flip_down":
            prev = _prev_valid(dir_list)
            return prev is not None and prev == 1 and cur_dir == -1
        else:
            raise ValueError(f"Unknown operator for Parabolic SAR: {operator!r}")

    @staticmethod
    def _build_state(
        sar: list, direction: list,
        af_start: float, af_step: float, af_max: float,
        candles: list[Candle],
        _af: float | None = None, _ep: float | None = None,
    ) -> dict[str, Any]:
        return {
            "sar": sar,
            "direction": direction,
            "af_start": af_start,
            "af_step": af_step,
            "af_max": af_max,
            "_af": _af if _af is not None else af_start,
            "_ep": _ep if _ep is not None else 0.0,
            "_prev_high": candles[-1].high if candles else 0.0,
            "_prev_low": candles[-1].low if candles else 0.0,
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
