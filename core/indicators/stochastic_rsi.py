"""Stochastic RSI.

Applies the Stochastic Oscillator formula to RSI values instead of
price.  This makes it more sensitive than plain RSI and produces
faster signals.  Oscillates between 0 and 1 (or 0 and 100).

Operators supported:
    overbought  - StochRSI %K > value (default 0.8)
    oversold    - StochRSI %K < value (default 0.2)
    cross_up    - %K crossed above %D (bullish)
    cross_down  - %K crossed below %D (bearish)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class StochasticRSI(BaseIndicator):
    name = "Stochastic RSI"
    key = "stochastic_rsi"
    category = "momentum"
    default_params = {"rsi_period": 14, "stoch_period": 14, "k_smooth": 3, "d_smooth": 3}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
