"""True Strength Index (TSI).

A double-smoothed momentum oscillator that shows both the direction
and strength of a trend.  Uses double exponential smoothing of price
changes to filter noise.  Often paired with a signal line for
crossover entries.

Operators supported:
    above_zero    - TSI > 0 (bullish momentum)
    below_zero    - TSI < 0 (bearish momentum)
    cross_up      - TSI crossed above signal line
    cross_down    - TSI crossed below signal line
    rising        - TSI is increasing
    falling       - TSI is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class TSI(BaseIndicator):
    name = "True Strength Index"
    key = "tsi"
    category = "momentum"
    default_params = {"long_period": 25, "short_period": 13, "signal_period": 7}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
