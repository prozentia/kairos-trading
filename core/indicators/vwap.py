"""Volume Weighted Average Price (VWAP).

The average price weighted by volume, typically calculated from the
start of the trading session.  Institutional traders use VWAP as a
benchmark; price above VWAP suggests bullish sentiment and below
suggests bearish.

For crypto (24/7 markets), we compute VWAP over a rolling window
rather than session-based.  The rolling window uses all available
candles by default.

Operators supported:
    price_above   - current close > VWAP
    price_below   - current close < VWAP
    cross_up      - price just crossed above VWAP
    cross_down    - price just crossed below VWAP
    deviation     - price distance from VWAP as percentage > value
"""

from __future__ import annotations

import math
from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class VWAP(BaseIndicator):
    name = "Volume Weighted Average Price"
    key = "vwap"
    category = "volume"
    default_params = {"reset_period": "session", "band_multiplier": 2.0}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute VWAP over a full candle history.

        Uses typical price (H+L+C)/3 weighted by volume.

        Returns:
            vwap         - list of VWAP values
            upper_band   - list of VWAP + band_mult * std_dev
            lower_band   - list of VWAP - band_mult * std_dev
            prices       - list of close prices
        """
        p = self.merge_params(params)
        band_mult: float = p["band_multiplier"]

        n = len(candles)
        vwap_values: list[float | None] = [None] * n
        upper_band: list[float | None] = [None] * n
        lower_band: list[float | None] = [None] * n
        prices: list[float] = [c.close for c in candles]

        if n == 0:
            return self._build_state(vwap_values, upper_band, lower_band, prices)

        cumulative_tpv = 0.0  # cumulative (typical_price * volume)
        cumulative_vol = 0.0  # cumulative volume
        cumulative_tpv2 = 0.0  # for standard deviation

        for i in range(n):
            tp = (candles[i].high + candles[i].low + candles[i].close) / 3.0
            vol = candles[i].volume
            cumulative_tpv += tp * vol
            cumulative_vol += vol
            cumulative_tpv2 += tp * tp * vol

            if cumulative_vol > 0:
                vwap_val = cumulative_tpv / cumulative_vol
                vwap_values[i] = vwap_val

                # VWAP standard deviation
                variance = (cumulative_tpv2 / cumulative_vol) - (vwap_val * vwap_val)
                std = math.sqrt(max(variance, 0.0))

                upper_band[i] = vwap_val + band_mult * std
                lower_band[i] = vwap_val - band_mult * std

        return self._build_state(vwap_values, upper_band, lower_band, prices)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update VWAP with one new candle."""
        p = self.merge_params(params)
        band_mult: float = p["band_multiplier"]

        tp = (candle.high + candle.low + candle.close) / 3.0
        vol = candle.volume

        cumulative_tpv = state.get("_cumulative_tpv", 0.0) + tp * vol
        cumulative_vol = state.get("_cumulative_vol", 0.0) + vol
        cumulative_tpv2 = state.get("_cumulative_tpv2", 0.0) + tp * tp * vol

        state["_cumulative_tpv"] = cumulative_tpv
        state["_cumulative_vol"] = cumulative_vol
        state["_cumulative_tpv2"] = cumulative_tpv2
        state["prices"].append(candle.close)

        if cumulative_vol > 0:
            vwap_val = cumulative_tpv / cumulative_vol
            variance = (cumulative_tpv2 / cumulative_vol) - (vwap_val * vwap_val)
            std = math.sqrt(max(variance, 0.0))

            state["vwap"].append(vwap_val)
            state["upper_band"].append(vwap_val + band_mult * std)
            state["lower_band"].append(vwap_val - band_mult * std)
        else:
            state["vwap"].append(None)
            state["upper_band"].append(None)
            state["lower_band"].append(None)

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current VWAP state."""
        vwap_list = state.get("vwap", [])
        prices = state.get("prices", [])

        latest_vwap = _last_valid(vwap_list)
        price = prices[-1] if prices else None

        if operator == "price_above":
            if price is None or latest_vwap is None:
                return False
            return price > latest_vwap

        elif operator == "price_below":
            if price is None or latest_vwap is None:
                return False
            return price < latest_vwap

        elif operator == "cross_up":
            if len(prices) < 2 or len(vwap_list) < 2:
                return False
            prev_vwap = vwap_list[-2]
            prev_price = prices[-2]
            if prev_vwap is None or latest_vwap is None:
                return False
            return prev_price <= prev_vwap and price > latest_vwap

        elif operator == "cross_down":
            if len(prices) < 2 or len(vwap_list) < 2:
                return False
            prev_vwap = vwap_list[-2]
            prev_price = prices[-2]
            if prev_vwap is None or latest_vwap is None:
                return False
            return prev_price >= prev_vwap and price < latest_vwap

        elif operator == "deviation":
            # Percentage distance from VWAP
            if price is None or latest_vwap is None or latest_vwap == 0:
                return False
            deviation_pct = abs(price - latest_vwap) / latest_vwap * 100.0
            threshold = float(value) if value is not None else 1.0
            return deviation_pct > threshold

        else:
            raise ValueError(f"Unknown operator for VWAP: {operator!r}")

    @staticmethod
    def _build_state(
        vwap: list, upper_band: list, lower_band: list, prices: list,
    ) -> dict[str, Any]:
        return {
            "vwap": vwap,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "prices": prices,
        }


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value."""
    for v in reversed(values):
        if v is not None:
            return v
    return None
