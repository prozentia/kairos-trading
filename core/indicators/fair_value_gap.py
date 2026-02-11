"""Fair Value Gap (FVG) detector.

Identifies gaps in price action caused by aggressive buying or
selling.  A bullish FVG occurs when candle[i-1].high < candle[i+1].low,
leaving a gap that price tends to revisit.  A bearish FVG is the
inverse.  Popular in ICT (Inner Circle Trader) methodology.

Operators supported:
    in_bullish_fvg   - price is inside a bullish FVG zone
    in_bearish_fvg   - price is inside a bearish FVG zone
    near_bullish_fvg - price approaching a bullish FVG
    near_bearish_fvg - price approaching a bearish FVG
    fresh_bullish    - unmitigated bullish FVG exists
    fresh_bearish    - unmitigated bearish FVG exists
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class FairValueGap(BaseIndicator):
    name = "Fair Value Gap"
    key = "fair_value_gap"
    category = "special"
    default_params = {
        "lookback": 50,
        "min_gap_pct": 0.05,
        "proximity_pct": 0.1,
        "max_gaps": 10,
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
