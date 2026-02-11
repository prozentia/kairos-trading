"""Chaikin Money Flow (CMF).

Measures the amount of money flow volume over a period.  Calculated
from the accumulation/distribution value of each bar weighted by
volume.  Positive CMF indicates buying pressure, negative indicates
selling pressure.

Operators supported:
    positive     - CMF > 0 (buying pressure)
    negative     - CMF < 0 (selling pressure)
    above        - CMF > value
    below        - CMF < value
    rising       - CMF is increasing
    falling      - CMF is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class ChaikinMoneyFlow(BaseIndicator):
    name = "Chaikin Money Flow"
    key = "chaikin_money_flow"
    category = "volume"
    default_params = {"period": 20}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
