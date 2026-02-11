"""Heikin-Ashi candle transformation.

Smooths candlestick data to make trends and reversals easier to
identify.  HA candles use modified OHLC calculations that average
current and previous values, filtering out noise.

Operators supported:
    is_green         - current HA candle is green (close > open)
    is_red           - current HA candle is red (close < open)
    flip_to_green    - HA just changed from red to green
    flip_to_red      - HA just changed from green to red
    consecutive_green - N consecutive green candles
    consecutive_red   - N consecutive red candles
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class HeikinAshiIndicator(BaseIndicator):
    name = "Heikin Ashi"
    key = "heikin_ashi"
    category = "trend"
    default_params: dict[str, Any] = {}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
