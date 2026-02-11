"""Parabolic SAR (Stop and Reverse).

A trend-following indicator that places dots above or below price to
signal potential reversals.  The dots accelerate towards price as the
trend continues, making it useful as a trailing stop mechanism.

Operators supported:
    bullish     - SAR dots are below price (uptrend)
    bearish     - SAR dots are above price (downtrend)
    flip_up     - SAR just flipped from above to below price
    flip_down   - SAR just flipped from below to above price
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class ParabolicSAR(BaseIndicator):
    name = "Parabolic SAR"
    key = "parabolic_sar"
    category = "trend"
    default_params = {"af_start": 0.02, "af_step": 0.02, "af_max": 0.2}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
