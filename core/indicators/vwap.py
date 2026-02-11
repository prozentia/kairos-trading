"""Volume Weighted Average Price (VWAP).

The average price weighted by volume, typically calculated from the
start of the trading session.  Institutional traders use VWAP as a
benchmark; price above VWAP suggests bullish sentiment and below
suggests bearish.

Operators supported:
    price_above   - current close > VWAP
    price_below   - current close < VWAP
    cross_up      - price just crossed above VWAP
    cross_down    - price just crossed below VWAP
    deviation     - price distance from VWAP as percentage
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class VWAP(BaseIndicator):
    name = "Volume Weighted Average Price"
    key = "vwap"
    category = "volume"
    default_params = {"reset_period": "session"}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
