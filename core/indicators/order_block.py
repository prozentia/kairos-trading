"""Order Block detector.

Identifies institutional order blocks -- zones where large players
have placed significant orders, creating supply/demand imbalances.
A bullish order block is the last bearish candle before a strong
bullish move; a bearish order block is the last bullish candle before
a strong bearish move.

Operators supported:
    in_bullish_ob   - price is inside a bullish order block zone
    in_bearish_ob   - price is inside a bearish order block zone
    near_bullish_ob - price is approaching a bullish OB (within pct)
    near_bearish_ob - price is approaching a bearish OB (within pct)
    fresh_bullish   - unmitigated bullish OB detected
    fresh_bearish   - unmitigated bearish OB detected
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class OrderBlock(BaseIndicator):
    name = "Order Block"
    key = "order_block"
    category = "special"
    default_params = {
        "lookback": 20,
        "min_impulse_pct": 0.5,
        "proximity_pct": 0.1,
        "max_blocks": 5,
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
