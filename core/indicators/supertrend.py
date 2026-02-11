"""Supertrend indicator.

Combines ATR-based volatility bands with trend direction.  The
supertrend line flips between support (below price in uptrend) and
resistance (above price in downtrend).  Very popular for trailing
stop placement and trend-following entries.

Operators supported:
    uptrend       - price is above the supertrend line
    downtrend     - price is below the supertrend line
    flip_up       - supertrend just flipped to uptrend
    flip_down     - supertrend just flipped to downtrend
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class Supertrend(BaseIndicator):
    name = "Supertrend"
    key = "supertrend"
    category = "trend"
    default_params = {"period": 10, "multiplier": 3.0}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
