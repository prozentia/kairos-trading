"""Relative Strength Index (RSI).

A momentum oscillator that measures the speed and magnitude of price
changes on a 0-100 scale.  Traditionally, readings above 70 indicate
overbought conditions and below 30 indicate oversold.

Operators supported:
    above       - RSI > value (e.g. overbought check)
    below       - RSI < value (e.g. oversold check)
    cross_up    - RSI just crossed above value
    cross_down  - RSI just crossed below value
    rising      - RSI is increasing
    falling     - RSI is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class RSI(BaseIndicator):
    name = "Relative Strength Index"
    key = "rsi"
    category = "momentum"
    default_params = {"period": 14, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
