"""Exponential Moving Average (EMA).

Gives more weight to recent prices, making it more responsive to new
information than a Simple Moving Average.  Commonly used to identify
trend direction and dynamic support/resistance levels.

Operators supported:
    price_above  - current close > EMA value
    price_below  - current close < EMA value
    rising       - EMA is increasing
    falling      - EMA is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class EMA(BaseIndicator):
    name = "Exponential Moving Average"
    key = "ema"
    category = "trend"
    default_params = {"period": 20, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
