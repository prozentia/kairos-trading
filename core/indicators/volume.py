"""Volume analysis indicator.

Provides volume-based signals including volume spikes, moving average
of volume, and On-Balance Volume (OBV).  Volume confirmation is
essential for validating breakouts and trend strength.

Operators supported:
    spike          - current volume > multiplier * average volume
    above_average  - current volume > average volume
    below_average  - current volume < average volume
    obv_rising     - OBV is trending up (accumulation)
    obv_falling    - OBV is trending down (distribution)
    dry_up         - volume is very low relative to average
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class Volume(BaseIndicator):
    name = "Volume Analysis"
    key = "volume"
    category = "volume"
    default_params = {"ma_period": 20, "spike_multiplier": 2.0}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
