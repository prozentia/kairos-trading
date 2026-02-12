"""Chaikin Money Flow (CMF).

Measures the amount of money flow volume over a period.  Calculated
from the accumulation/distribution value of each bar weighted by
volume.  Positive CMF indicates buying pressure, negative indicates
selling pressure.

CMF = Sum(MFV, period) / Sum(Volume, period)
Where MFV = ((Close - Low) - (High - Close)) / (High - Low) * Volume

Operators supported:
    positive     - CMF > 0 (buying pressure)
    negative     - CMF < 0 (selling pressure)
    above        - CMF > value
    below        - CMF < value
    rising       - CMF is increasing
    falling      - CMF is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _money_flow_multiplier(candle: Candle) -> float:
    """Compute the Money Flow Multiplier for a candle.

    MFM = ((Close - Low) - (High - Close)) / (High - Low)
    Returns 0.0 if high == low (doji / zero range).
    """
    hl_range = candle.high - candle.low
    if hl_range == 0:
        return 0.0
    return ((candle.close - candle.low) - (candle.high - candle.close)) / hl_range


def _money_flow_volume(candle: Candle) -> float:
    """Compute Money Flow Volume = MFM * Volume."""
    return _money_flow_multiplier(candle) * candle.volume


@register
class ChaikinMoneyFlow(BaseIndicator):
    name = "Chaikin Money Flow"
    key = "chaikin_money_flow"
    category = "volume"
    default_params = {"period": 20}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute CMF over a full candle history.

        Returns:
            cmf        - list of CMF values (None for warm-up period)
            mfv        - list of money flow volume values
        """
        p = self.merge_params(params)
        period: int = p["period"]

        n = len(candles)
        cmf_values: list[float | None] = [None] * n
        mfv_values: list[float] = [_money_flow_volume(c) for c in candles]
        vol_values: list[float] = [c.volume for c in candles]

        if n < period:
            return {"cmf": cmf_values, "mfv": mfv_values, "volumes": vol_values}

        # Sliding window sum
        mfv_sum = sum(mfv_values[:period])
        vol_sum = sum(vol_values[:period])

        cmf_values[period - 1] = mfv_sum / vol_sum if vol_sum > 0 else 0.0

        for i in range(period, n):
            mfv_sum += mfv_values[i] - mfv_values[i - period]
            vol_sum += vol_values[i] - vol_values[i - period]
            cmf_values[i] = mfv_sum / vol_sum if vol_sum > 0 else 0.0

        return {"cmf": cmf_values, "mfv": mfv_values, "volumes": vol_values}

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update CMF with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]

        mfv = _money_flow_volume(candle)
        state["mfv"].append(mfv)
        state["volumes"].append(candle.volume)

        mfv_list = state["mfv"]
        vol_list = state["volumes"]
        n = len(mfv_list)

        if n < period:
            state["cmf"].append(None)
        else:
            window_mfv = mfv_list[-period:]
            window_vol = vol_list[-period:]
            mfv_sum = sum(window_mfv)
            vol_sum = sum(window_vol)
            cmf_val = mfv_sum / vol_sum if vol_sum > 0 else 0.0
            state["cmf"].append(cmf_val)

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current CMF state."""
        cmf_list = state.get("cmf", [])
        latest_cmf = _last_valid(cmf_list)

        if operator == "positive":
            if latest_cmf is None:
                return False
            return latest_cmf > 0.0

        elif operator == "negative":
            if latest_cmf is None:
                return False
            return latest_cmf < 0.0

        elif operator == "above":
            if latest_cmf is None or value is None:
                return False
            return latest_cmf > float(value)

        elif operator == "below":
            if latest_cmf is None or value is None:
                return False
            return latest_cmf < float(value)

        elif operator == "rising":
            prev_cmf = _find_prev_valid(cmf_list)
            if latest_cmf is None or prev_cmf is None:
                return False
            return latest_cmf > prev_cmf

        elif operator == "falling":
            prev_cmf = _find_prev_valid(cmf_list)
            if latest_cmf is None or prev_cmf is None:
                return False
            return latest_cmf < prev_cmf

        else:
            raise ValueError(f"Unknown operator for CMF: {operator!r}")


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value."""
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _find_prev_valid(values: list[float | None]) -> float | None:
    """Return the second-to-last non-None value."""
    found_last = False
    for v in reversed(values):
        if v is not None:
            if found_last:
                return v
            found_last = True
    return None
