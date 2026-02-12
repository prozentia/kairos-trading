"""Average True Range (ATR).

Measures market volatility by calculating the average of true ranges
over a period.  True range is the greatest of: current high-low,
abs(high - previous close), abs(low - previous close).  Widely used
for stop-loss placement and position sizing.

Operators supported:
    above       - ATR > value
    below       - ATR < value
    rising      - ATR is increasing (volatility expanding)
    falling     - ATR is decreasing (volatility contracting)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _true_range(high: float, low: float, prev_close: float) -> float:
    """Compute the true range for a single bar."""
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close),
    )


@register
class ATR(BaseIndicator):
    name = "Average True Range"
    key = "atr"
    category = "volatility"
    default_params = {"period": 14}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute ATR over a full candle history.

        Uses the Wilder smoothing method (RMA):
            ATR[0]  = mean of first `period` true ranges
            ATR[n]  = (ATR[n-1] * (period-1) + TR[n]) / period

        Returns:
            atr       - list of ATR values (None for warm-up entries)
            tr        - list of true range values
            prev_close - the close of the last candle (for incremental update)
        """
        p = self.merge_params(params)
        period: int = p["period"]

        n = len(candles)
        atr_values: list[float | None] = [None] * n
        tr_values: list[float | None] = [None] * n

        if n == 0:
            return {"atr": atr_values, "tr": tr_values, "prev_close": 0.0}

        # First candle: TR = high - low (no previous close)
        tr_values[0] = candles[0].high - candles[0].low

        for i in range(1, n):
            tr_values[i] = _true_range(
                candles[i].high, candles[i].low, candles[i - 1].close
            )

        if n < period + 1:
            return {
                "atr": atr_values,
                "tr": tr_values,
                "prev_close": candles[-1].close,
            }

        # Seed ATR: simple average of first `period` true ranges (indices 1..period)
        seed_sum = sum(tr_values[i] for i in range(1, period + 1))
        atr_seed = seed_sum / period
        atr_values[period] = atr_seed

        # Wilder smoothing for subsequent values
        prev_atr = atr_seed
        for i in range(period + 1, n):
            current_atr = (prev_atr * (period - 1) + tr_values[i]) / period
            atr_values[i] = current_atr
            prev_atr = current_atr

        return {
            "atr": atr_values,
            "tr": tr_values,
            "prev_close": candles[-1].close,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update ATR with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]

        prev_close = state.get("prev_close", candle.open)
        tr = _true_range(candle.high, candle.low, prev_close)

        state["tr"].append(tr)

        # Find last valid ATR
        prev_atr = _last_valid(state["atr"])

        if prev_atr is not None:
            new_atr = (prev_atr * (period - 1) + tr) / period
            state["atr"].append(new_atr)
        else:
            # Check if we have enough TR values to compute the seed
            tr_list = state["tr"]
            valid_trs = [v for v in tr_list if v is not None]
            if len(valid_trs) >= period:
                # Use the last `period` TRs
                new_atr = sum(valid_trs[-period:]) / period
                state["atr"].append(new_atr)
            else:
                state["atr"].append(None)

        state["prev_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current ATR state."""
        atr_list = state.get("atr", [])
        latest_atr = _last_valid(atr_list)

        if operator == "above":
            if latest_atr is None or value is None:
                return False
            return latest_atr > float(value)

        elif operator == "below":
            if latest_atr is None or value is None:
                return False
            return latest_atr < float(value)

        elif operator == "rising":
            prev_atr = _find_prev_valid(atr_list)
            if latest_atr is None or prev_atr is None:
                return False
            return latest_atr > prev_atr

        elif operator == "falling":
            prev_atr = _find_prev_valid(atr_list)
            if latest_atr is None or prev_atr is None:
                return False
            return latest_atr < prev_atr

        else:
            raise ValueError(f"Unknown operator for ATR: {operator!r}")


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value."""
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _find_prev_valid(values: list[float | None]) -> float | None:
    """Return the second-to-last non-None value."""
    found_last = False
    for v in reversed(values):
        if v is not None:
            if found_last:
                return v
            found_last = True
    return None
