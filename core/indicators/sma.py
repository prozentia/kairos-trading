"""Simple Moving Average (SMA).

The arithmetic mean of the last *period* closing prices.  Useful as
a baseline trend filter and for building other indicators (e.g.
Bollinger Bands).

Operators supported:
    price_above  - current close > SMA value
    price_below  - current close < SMA value
    rising       - SMA is increasing
    falling      - SMA is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class SMA(BaseIndicator):
    name = "Simple Moving Average"
    key = "sma"
    category = "trend"
    default_params = {"period": 20, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
