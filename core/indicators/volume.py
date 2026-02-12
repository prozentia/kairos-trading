"""Volume analysis indicator.

Provides volume-based signals including volume spikes, moving average
of volume, and On-Balance Volume (OBV).  Volume confirmation is
essential for validating breakouts and trend strength.

Operators supported:
    spike          - current volume > multiplier * average volume
    above_average  - current volume > average volume
    below_average  - current volume < average volume
    obv_rising     - OBV is trending up (accumulation)
    obv_falling    - OBV is trending down (distribution)
    dry_up         - volume is very low relative to average
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class Volume(BaseIndicator):
    name = "Volume Analysis"
    key = "volume"
    category = "volume"
    default_params = {"ma_period": 20, "spike_multiplier": 2.0}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute volume analysis over a full candle history.

        Returns:
            volumes   - list of raw volume values
            vol_sma   - list of volume SMA values
            vol_ratio - list of volume / SMA ratio
            obv       - list of On-Balance Volume values
        """
        p = self.merge_params(params)
        ma_period: int = p["ma_period"]

        n = len(candles)
        volumes: list[float] = [c.volume for c in candles]
        vol_sma: list[float | None] = [None] * n
        vol_ratio: list[float | None] = [None] * n
        obv: list[float] = [0.0] * n

        if n == 0:
            return self._build_state(volumes, vol_sma, vol_ratio, obv)

        # Compute OBV
        obv[0] = volumes[0]
        for i in range(1, n):
            if candles[i].close > candles[i - 1].close:
                obv[i] = obv[i - 1] + volumes[i]
            elif candles[i].close < candles[i - 1].close:
                obv[i] = obv[i - 1] - volumes[i]
            else:
                obv[i] = obv[i - 1]

        # Compute volume SMA and ratio
        if n >= ma_period:
            window_sum = sum(volumes[:ma_period])
            vol_sma[ma_period - 1] = window_sum / ma_period
            if vol_sma[ma_period - 1] > 0:
                vol_ratio[ma_period - 1] = volumes[ma_period - 1] / vol_sma[ma_period - 1]

            for i in range(ma_period, n):
                window_sum += volumes[i] - volumes[i - ma_period]
                sma_val = window_sum / ma_period
                vol_sma[i] = sma_val
                if sma_val > 0:
                    vol_ratio[i] = volumes[i] / sma_val
                else:
                    vol_ratio[i] = 0.0

        return self._build_state(volumes, vol_sma, vol_ratio, obv)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update volume analysis with one new candle."""
        p = self.merge_params(params)
        ma_period: int = p["ma_period"]

        vol = candle.volume
        state["volumes"].append(vol)
        volumes = state["volumes"]
        n = len(volumes)

        # Update OBV
        obv_list = state["obv"]
        prev_obv = obv_list[-1] if obv_list else 0.0
        prev_close = state.get("_prev_close", candle.open)

        if candle.close > prev_close:
            new_obv = prev_obv + vol
        elif candle.close < prev_close:
            new_obv = prev_obv - vol
        else:
            new_obv = prev_obv
        obv_list.append(new_obv)

        # Update volume SMA
        if n >= ma_period:
            window = volumes[-ma_period:]
            sma_val = sum(window) / ma_period
            state["vol_sma"].append(sma_val)
            ratio = vol / sma_val if sma_val > 0 else 0.0
            state["vol_ratio"].append(ratio)
        else:
            state["vol_sma"].append(None)
            state["vol_ratio"].append(None)

        state["_prev_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current volume state."""
        volumes = state.get("volumes", [])
        vol_sma = state.get("vol_sma", [])
        vol_ratio = state.get("vol_ratio", [])
        obv = state.get("obv", [])

        current_vol = volumes[-1] if volumes else None
        current_sma = _last_valid(vol_sma)
        current_ratio = _last_valid(vol_ratio)

        if operator == "spike":
            spike_mult = float(value) if value is not None else 2.0
            if current_ratio is None:
                return False
            return current_ratio > spike_mult

        elif operator == "above_average":
            if current_ratio is None:
                return False
            return current_ratio > 1.0

        elif operator == "below_average":
            if current_ratio is None:
                return False
            return current_ratio < 1.0

        elif operator == "obv_rising":
            if len(obv) < 2:
                return False
            return obv[-1] > obv[-2]

        elif operator == "obv_falling":
            if len(obv) < 2:
                return False
            return obv[-1] < obv[-2]

        elif operator == "dry_up":
            # Volume below 50% of average
            threshold = float(value) if value is not None else 0.5
            if current_ratio is None:
                return False
            return current_ratio < threshold

        else:
            raise ValueError(f"Unknown operator for Volume: {operator!r}")

    @staticmethod
    def _build_state(
        volumes: list, vol_sma: list, vol_ratio: list, obv: list,
    ) -> dict[str, Any]:
        return {
            "volumes": volumes,
            "vol_sma": vol_sma,
            "vol_ratio": vol_ratio,
            "obv": obv,
        }


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value."""
    for v in reversed(values):
        if v is not None:
            return v
    return None
