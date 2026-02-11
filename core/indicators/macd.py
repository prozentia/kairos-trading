"""Moving Average Convergence Divergence (MACD).

Shows the relationship between two EMAs.  The MACD line is the
difference between the fast and slow EMAs, and the signal line is an
EMA of the MACD line.  The histogram visualises the gap between them.

Operators supported:
    cross_up       - MACD crossed above signal line (bullish)
    cross_down     - MACD crossed below signal line (bearish)
    above_zero     - MACD line is positive
    below_zero     - MACD line is negative
    histogram_rising  - histogram is increasing
    histogram_falling - histogram is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class MACD(BaseIndicator):
    name = "MACD"
    key = "macd"
    category = "momentum"
    default_params = {"fast_period": 12, "slow_period": 26, "signal_period": 9, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
