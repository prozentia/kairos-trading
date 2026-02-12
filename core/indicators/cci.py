"""Commodity Channel Index (CCI).

Measures the deviation of price from its statistical mean.  Values
above +100 suggest an overbought condition (strong uptrend), while
values below -100 suggest an oversold condition (strong downtrend).

Calculation:
    Typical Price (TP) = (high + low + close) / 3
    SMA of TP over N periods
    Mean Deviation = average of |TP - SMA(TP)| over N periods
    CCI = (TP - SMA(TP)) / (constant * Mean Deviation)

Operators supported:
    above        - CCI > value
    below        - CCI < value
    overbought   - CCI > +100
    oversold     - CCI < -100
    cross_up     - CCI just crossed above value
    cross_down   - CCI just crossed below value
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class CCI(BaseIndicator):
    name = "Commodity Channel Index"
    key = "cci"
    category = "momentum"
    default_params = {"period": 20, "constant": 0.015}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute CCI over a full candle history.

        Returns dict with:
            cci         - list of CCI values (None for warmup period)
            prev_cci    - previous CCI value (for crossover detection)
            current_cci - latest CCI value
            tp_buffer   - recent typical prices for incremental updates
        """
        p = self.merge_params(params)
        period: int = p["period"]
        constant: float = p["constant"]

        n = len(candles)
        cci_values: list[float | None] = [None] * n

        # Compute all typical prices
        tp_list = [(c.high + c.low + c.close) / 3.0 for c in candles]

        if n < period:
            return {
                "cci": cci_values,
                "prev_cci": None,
                "current_cci": None,
                "tp_buffer": tp_list[:],
            }

        for i in range(period - 1, n):
            window = tp_list[i - period + 1: i + 1]
            tp_sma = sum(window) / period

            # Mean deviation
            mean_dev = sum(abs(tp - tp_sma) for tp in window) / period

            if mean_dev == 0.0:
                cci_values[i] = 0.0
            else:
                cci_values[i] = (tp_list[i] - tp_sma) / (constant * mean_dev)

        prev_cci = cci_values[-2] if n >= 2 else None
        current_cci = cci_values[-1] if n > 0 else None

        # Store recent TP values for incremental updates
        tp_buffer = tp_list[-(period):] if n >= period else tp_list[:]

        return {
            "cci": cci_values,
            "prev_cci": prev_cci,
            "current_cci": current_cci,
            "tp_buffer": tp_buffer,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update CCI with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]
        constant: float = p["constant"]

        tp_buffer: list[float] = state["tp_buffer"]
        new_tp = (candle.high + candle.low + candle.close) / 3.0

        tp_buffer.append(new_tp)
        if len(tp_buffer) > period:
            tp_buffer.pop(0)

        new_cci = None
        if len(tp_buffer) >= period:
            tp_sma = sum(tp_buffer) / period
            mean_dev = sum(abs(tp - tp_sma) for tp in tp_buffer) / period

            if mean_dev == 0.0:
                new_cci = 0.0
            else:
                new_cci = (new_tp - tp_sma) / (constant * mean_dev)

        state["prev_cci"] = state.get("current_cci")
        state["current_cci"] = new_cci
        state["cci"].append(new_cci)
        state["tp_buffer"] = tp_buffer

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate CCI conditions.

        Supported operators:
            above      - CCI > value
            below      - CCI < value
            overbought - CCI > +100
            oversold   - CCI < -100
            cross_up   - CCI crossed above value
            cross_down - CCI crossed below value
        """
        current = state.get("current_cci")
        prev = state.get("prev_cci")

        if operator == "above":
            return current is not None and current > float(value)

        if operator == "below":
            return current is not None and current < float(value)

        if operator == "overbought":
            threshold = float(value) if value is not None else 100.0
            return current is not None and current > threshold

        if operator == "oversold":
            threshold = float(value) if value is not None else -100.0
            return current is not None and current < threshold

        if operator == "cross_up":
            if current is None or prev is None:
                return False
            threshold = float(value) if value is not None else 0.0
            return prev <= threshold and current > threshold

        if operator == "cross_down":
            if current is None or prev is None:
                return False
            threshold = float(value) if value is not None else 0.0
            return prev >= threshold and current < threshold

        raise ValueError(f"Unknown CCI operator: {operator!r}")
