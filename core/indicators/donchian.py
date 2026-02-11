"""Donchian Channel.

Plots the highest high and lowest low over the last *period* candles.
The middle line is the average of the upper and lower bands.  Used in
breakout strategies (e.g. Turtle Trading) and as a volatility measure.

Operators supported:
    breakout_up    - price closed above the upper band
    breakout_down  - price closed below the lower band
    inside         - price is between the bands
    squeeze        - channel width is narrowing (low volatility)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class DonchianChannel(BaseIndicator):
    name = "Donchian Channel"
    key = "donchian"
    category = "trend"
    default_params = {"period": 20}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
