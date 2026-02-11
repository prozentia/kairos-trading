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

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class BollingerBands(BaseIndicator):
    name = "Bollinger Bands"
    key = "bollinger"
    category = "volatility"
    default_params = {"period": 20, "std_dev": 2.0, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
