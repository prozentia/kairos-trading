"""Average Directional Index with Directional Movement (ADX/DMI).

ADX measures the *strength* of a trend (not direction).  +DI and -DI
show the directional movement.  ADX above 25 indicates a strong trend;
+DI > -DI suggests bullish direction and vice versa.

Operators supported:
    trending       - ADX > value (default 25, strong trend)
    not_trending   - ADX < value (default 20, ranging)
    bullish        - +DI > -DI
    bearish        - -DI > +DI
    di_cross_up    - +DI just crossed above -DI
    di_cross_down  - -DI just crossed above +DI
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class ADXDMI(BaseIndicator):
    name = "ADX / DMI"
    key = "adx_dmi"
    category = "volatility"
    default_params = {"period": 14}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        raise NotImplementedError

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        raise NotImplementedError
