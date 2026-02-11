"""Rate of Change (ROC).

Measures the percentage change in price between the current close and
the close *period* bars ago.  Positive values indicate upward momentum,
negative values indicate downward momentum.

Operators supported:
    above       - ROC > value
    below       - ROC < value
    positive    - ROC > 0
    negative    - ROC < 0
    rising      - ROC is increasing
    falling     - ROC is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class ROC(BaseIndicator):
    name = "Rate of Change"
    key = "roc"
    category = "momentum"
    default_params = {"period": 12, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
