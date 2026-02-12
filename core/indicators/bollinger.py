"""Bollinger Bands.

A volatility indicator consisting of a middle SMA band and upper/lower
bands placed *std_dev* standard deviations away.  Bands widen during
high volatility and contract during low volatility (squeeze).  Price
touching the lower band can signal oversold conditions.

Operators supported:
    touch_upper    - price >= upper band
    touch_lower    - price <= lower band
    inside         - price is between the bands
    squeeze        - bandwidth is below threshold (low volatility)
    expansion      - bandwidth is above threshold (high volatility)
    percent_b_above - %B > value
    percent_b_below - %B < value
"""

from __future__ import annotations

import math
from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _get_source(candle: Candle, source: str) -> float:
    """Extract a price field from a candle by name."""
    return float(getattr(candle, source))


@register
class BollingerBands(BaseIndicator):
    name = "Bollinger Bands"
    key = "bollinger"
    category = "volatility"
    default_params = {"period": 20, "std_dev": 2.0, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Bollinger Bands over a full candle history.

        Returns:
            upper      - list of upper band values
            middle     - list of middle band (SMA) values
            lower      - list of lower band values
            bandwidth  - list of bandwidth values (upper-lower)/middle
            percent_b  - list of %B values (price-lower)/(upper-lower)
            prices     - list of source prices for reference
        """
        p = self.merge_params(params)
        period: int = p["period"]
        std_dev: float = p["std_dev"]
        source: str = p["source"]

        n = len(candles)
        upper: list[float | None] = [None] * n
        middle: list[float | None] = [None] * n
        lower: list[float | None] = [None] * n
        bandwidth: list[float | None] = [None] * n
        percent_b: list[float | None] = [None] * n
        prices: list[float] = [_get_source(c, source) for c in candles]

        if n < period:
            return self._build_state(
                upper, middle, lower, bandwidth, percent_b, prices
            )

        # Compute using a sliding window
        window_sum = sum(prices[:period])
        window_sq_sum = sum(p_val * p_val for p_val in prices[:period])

        for i in range(period - 1, n):
            if i > period - 1:
                # Slide the window
                old_val = prices[i - period]
                new_val = prices[i]
                window_sum += new_val - old_val
                window_sq_sum += new_val * new_val - old_val * old_val

            sma = window_sum / period
            # Population standard deviation
            variance = (window_sq_sum / period) - (sma * sma)
            std = math.sqrt(max(variance, 0.0))

            upper[i] = sma + std_dev * std
            middle[i] = sma
            lower[i] = sma - std_dev * std

            if sma > 0:
                bandwidth[i] = (upper[i] - lower[i]) / sma
            else:
                bandwidth[i] = 0.0

            band_width_abs = upper[i] - lower[i]
            if band_width_abs > 0:
                percent_b[i] = (prices[i] - lower[i]) / band_width_abs
            else:
                percent_b[i] = 0.5

        return self._build_state(
            upper, middle, lower, bandwidth, percent_b, prices
        )

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Bollinger Bands with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]
        std_dev: float = p["std_dev"]
        source: str = p["source"]

        price = _get_source(candle, source)
        state["prices"].append(price)
        prices = state["prices"]
        n = len(prices)

        if n < period:
            state["upper"].append(None)
            state["middle"].append(None)
            state["lower"].append(None)
            state["bandwidth"].append(None)
            state["percent_b"].append(None)
            return state

        # Compute SMA and std dev over the last `period` values
        window = prices[-period:]
        sma = sum(window) / period
        variance = sum((v - sma) ** 2 for v in window) / period
        std = math.sqrt(max(variance, 0.0))

        u = sma + std_dev * std
        l = sma - std_dev * std

        state["upper"].append(u)
        state["middle"].append(sma)
        state["lower"].append(l)

        bw = (u - l) / sma if sma > 0 else 0.0
        state["bandwidth"].append(bw)

        band_diff = u - l
        pb = (price - l) / band_diff if band_diff > 0 else 0.5
        state["percent_b"].append(pb)

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current Bollinger Bands state."""
        upper = _last_valid(state.get("upper", []))
        middle = _last_valid(state.get("middle", []))
        lower = _last_valid(state.get("lower", []))
        bw = _last_valid(state.get("bandwidth", []))
        pb = _last_valid(state.get("percent_b", []))
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

        elif operator == "squeeze":
            if bw is None or value is None:
                return False
            return bw < float(value)

        elif operator == "expansion":
            if bw is None or value is None:
                return False
            return bw > float(value)

        elif operator == "percent_b_above":
            if pb is None or value is None:
                return False
            return pb > float(value)

        elif operator == "percent_b_below":
            if pb is None or value is None:
                return False
            return pb < float(value)

        else:
            raise ValueError(f"Unknown operator for Bollinger: {operator!r}")

    @staticmethod
    def _build_state(
        upper: list, middle: list, lower: list,
        bandwidth: list, percent_b: list, prices: list,
    ) -> dict[str, Any]:
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "bandwidth": bandwidth,
            "percent_b": percent_b,
            "prices": prices,
        }


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value in a list."""
    for v in reversed(values):
        if v is not None:
            return v
    return None
