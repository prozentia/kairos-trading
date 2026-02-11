"""Average True Range (ATR).

Measures market volatility by calculating the average of true ranges
over a period.  True range is the greatest of: current high-low,
abs(high - previous close), abs(low - previous close).  Widely used
for stop-loss placement and position sizing.

Operators supported:
    above       - ATR > value
    below       - ATR < value
    rising      - ATR is increasing (volatility expanding)
    falling     - ATR is decreasing (volatility contracting)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class ATR(BaseIndicator):
    name = "Average True Range"
    key = "atr"
    category = "volatility"
    default_params = {"period": 14}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
