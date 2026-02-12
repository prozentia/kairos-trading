"""Rate of Change (ROC).

Measures the percentage change in price between the current close and
the close *period* bars ago.  Positive values indicate upward momentum,
negative values indicate downward momentum.

Calculation:
    ROC = ((close - close_n_ago) / close_n_ago) * 100

Operators supported:
    above       - ROC > value
    below       - ROC < value
    positive    - ROC > 0
    negative    - ROC < 0
    rising      - ROC is increasing
    falling     - ROC is decreasing
    cross_up    - ROC crossed above value
    cross_down  - ROC crossed below value
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
        """Compute ROC over a full candle history.

        Returns dict with:
            roc         - list of ROC values (None for warmup)
            prev_roc    - previous ROC value
            current_roc - latest ROC value
            price_buffer - recent prices for incremental updates
        """
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        prices = [getattr(c, source) for c in candles]
        n = len(prices)
        roc_values: list[float | None] = [None] * n

        if n <= period:
            return {
                "roc": roc_values,
                "prev_roc": None,
                "current_roc": None,
                "price_buffer": prices[:],
            }

        for i in range(period, n):
            old_price = prices[i - period]
            if old_price != 0.0:
                roc_values[i] = ((prices[i] - old_price) / old_price) * 100.0
            else:
                roc_values[i] = 0.0

        prev_roc = roc_values[-2] if n >= 2 else None
        current_roc = roc_values[-1] if n > 0 else None

        # Store recent prices for incremental updates (need at least period + 1)
        buffer_size = period + 1
        price_buffer = prices[-buffer_size:] if n >= buffer_size else prices[:]

        return {
            "roc": roc_values,
            "prev_roc": prev_roc,
            "current_roc": current_roc,
            "price_buffer": price_buffer,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update ROC with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]
        source: str = p["source"]

        new_price = getattr(candle, source)
        price_buffer: list[float] = state["price_buffer"]

        price_buffer.append(new_price)
        buffer_size = period + 1
        if len(price_buffer) > buffer_size:
            price_buffer.pop(0)

        new_roc = None
        if len(price_buffer) > period:
            old_price = price_buffer[0]
            if old_price != 0.0:
                new_roc = ((new_price - old_price) / old_price) * 100.0
            else:
                new_roc = 0.0

        state["prev_roc"] = state.get("current_roc")
        state["current_roc"] = new_roc
        state["roc"].append(new_roc)
        state["price_buffer"] = price_buffer

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate ROC conditions.

        Supported operators:
            above      - ROC > value
            below      - ROC < value
            positive   - ROC > 0
            negative   - ROC < 0
            rising     - ROC is increasing
            falling    - ROC is decreasing
            cross_up   - ROC crossed above value (default 0)
            cross_down - ROC crossed below value (default 0)
        """
        current = state.get("current_roc")
        prev = state.get("prev_roc")

        if operator == "above":
            return current is not None and current > float(value)

        if operator == "below":
            return current is not None and current < float(value)

        if operator == "positive":
            return current is not None and current > 0.0

        if operator == "negative":
            return current is not None and current < 0.0

        if operator == "rising":
            if current is None or prev is None:
                return False
            return current > prev

        if operator == "falling":
            if current is None or prev is None:
                return False
            return current < prev

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

        raise ValueError(f"Unknown ROC operator: {operator!r}")
