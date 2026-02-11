"""EMA Crossover detector.

Tracks two EMAs (fast and slow) and detects golden crosses (fast
crosses above slow) and death crosses (fast crosses below slow).
A classic trend-following entry/exit signal.

Operators supported:
    golden_cross  - fast EMA just crossed above slow EMA
    death_cross   - fast EMA just crossed below slow EMA
    bullish       - fast EMA > slow EMA (trend confirmation)
    bearish       - fast EMA < slow EMA
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class EMACross(BaseIndicator):
    name = "EMA Crossover"
    key = "ema_cross"
    category = "trend"
    default_params = {"fast_period": 9, "slow_period": 21, "source": "close"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
