"""Moving Average Convergence Divergence (MACD).

Shows the relationship between two EMAs.  The MACD line is the
difference between the fast and slow EMAs, and the signal line is an
EMA of the MACD line.  The histogram visualises the gap between them.

Operators supported:
    cross_up          - MACD crossed above signal line (bullish)
    cross_down        - MACD crossed below signal line (bearish)
    above_zero        - MACD line is positive
    below_zero        - MACD line is negative
    histogram_positive - histogram > 0
    histogram_negative - histogram < 0
    histogram_rising  - histogram is increasing
    histogram_falling - histogram is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _ema_multiplier(period: int) -> float:
    """EMA smoothing factor: 2 / (period + 1)."""
    return 2.0 / (period + 1)


def _compute_ema_series(values: list[float], period: int) -> list[float | None]:
    """Compute full EMA series over a list of values.

    Returns a list of the same length; the first (period - 1) entries
    are None, the value at index (period - 1) is the SMA seed.
    """
    n = len(values)
    result: list[float | None] = [None] * n

    if n < period:
        return result

    # SMA seed
    sma = sum(values[:period]) / period
    result[period - 1] = sma

    k = _ema_multiplier(period)
    prev = sma
    for i in range(period, n):
        ema_val = values[i] * k + prev * (1.0 - k)
        result[i] = ema_val
        prev = ema_val

    return result


@register
class MACD(BaseIndicator):
    name = "MACD"
    key = "macd"
    category = "momentum"
    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "source": "close",
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute MACD over a full candle history.

        Returns dict with:
            macd_line      - list of MACD values (fast EMA - slow EMA)
            signal_line    - list of signal EMA values
            histogram      - list of histogram values (macd - signal)
            fast_ema       - list of fast EMA values
            slow_ema       - list of slow EMA values
            prev_macd      - previous MACD value
            prev_signal    - previous signal value
            prev_histogram - previous histogram value
            current_macd   - latest MACD value
            current_signal - latest signal value
            current_histogram - latest histogram value
        """
        p = self.merge_params(params)
        fast_period: int = p["fast_period"]
        slow_period: int = p["slow_period"]
        signal_period: int = p["signal_period"]
        source: str = p["source"]

        prices = [getattr(c, source) for c in candles]
        n = len(prices)

        # Compute fast and slow EMAs
        fast_ema = _compute_ema_series(prices, fast_period)
        slow_ema = _compute_ema_series(prices, slow_period)

        # MACD line = fast EMA - slow EMA
        macd_line: list[float | None] = [None] * n
        macd_raw: list[float] = []

        for i in range(n):
            if fast_ema[i] is not None and slow_ema[i] is not None:
                val = fast_ema[i] - slow_ema[i]
                macd_line[i] = val
                macd_raw.append(val)

        # Signal line = EMA of MACD line
        signal_line: list[float | None] = [None] * n
        histogram: list[float | None] = [None] * n

        if len(macd_raw) >= signal_period:
            signal_ema = _compute_ema_series(macd_raw, signal_period)
            # Map signal_ema back to original indices
            macd_start = n - len(macd_raw)
            for j, sig_val in enumerate(signal_ema):
                idx = macd_start + j
                signal_line[idx] = sig_val
                if sig_val is not None and macd_line[idx] is not None:
                    histogram[idx] = macd_line[idx] - sig_val

        # Extract state for incremental updates
        current_macd = macd_line[-1] if n > 0 else None
        current_signal = signal_line[-1] if n > 0 else None
        current_histogram = histogram[-1] if n > 0 else None

        # Previous values for crossover detection
        prev_macd = macd_line[-2] if n >= 2 else None
        prev_signal = signal_line[-2] if n >= 2 else None
        prev_histogram = histogram[-2] if n >= 2 else None

        # Store last EMA values for incremental update
        last_fast_ema = fast_ema[-1] if n > 0 else None
        last_slow_ema = slow_ema[-1] if n > 0 else None
        last_signal_ema = current_signal

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
            "fast_ema": fast_ema,
            "slow_ema": slow_ema,
            "last_fast_ema": last_fast_ema,
            "last_slow_ema": last_slow_ema,
            "last_signal_ema": last_signal_ema,
            "prev_macd": prev_macd,
            "prev_signal": prev_signal,
            "prev_histogram": prev_histogram,
            "current_macd": current_macd,
            "current_signal": current_signal,
            "current_histogram": current_histogram,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update MACD with one new candle."""
        p = self.merge_params(params)
        fast_period: int = p["fast_period"]
        slow_period: int = p["slow_period"]
        signal_period: int = p["signal_period"]
        source: str = p["source"]

        price = getattr(candle, source)

        last_fast = state.get("last_fast_ema")
        last_slow = state.get("last_slow_ema")
        last_signal = state.get("last_signal_ema")

        if last_fast is None or last_slow is None:
            return state

        # Update fast and slow EMAs
        k_fast = _ema_multiplier(fast_period)
        k_slow = _ema_multiplier(slow_period)

        new_fast = price * k_fast + last_fast * (1.0 - k_fast)
        new_slow = price * k_slow + last_slow * (1.0 - k_slow)
        new_macd = new_fast - new_slow

        # Update signal EMA
        if last_signal is not None:
            k_sig = _ema_multiplier(signal_period)
            new_signal = new_macd * k_sig + last_signal * (1.0 - k_sig)
        else:
            new_signal = None

        new_histogram = None
        if new_signal is not None:
            new_histogram = new_macd - new_signal

        # Shift current to prev
        state["prev_macd"] = state.get("current_macd")
        state["prev_signal"] = state.get("current_signal")
        state["prev_histogram"] = state.get("current_histogram")

        state["current_macd"] = new_macd
        state["current_signal"] = new_signal
        state["current_histogram"] = new_histogram
        state["last_fast_ema"] = new_fast
        state["last_slow_ema"] = new_slow
        state["last_signal_ema"] = new_signal

        # Append to series
        state["macd_line"].append(new_macd)
        state["signal_line"].append(new_signal)
        state["histogram"].append(new_histogram)
        state["fast_ema"].append(new_fast)
        state["slow_ema"].append(new_slow)

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate MACD conditions.

        Supported operators:
            cross_up          - MACD crossed above signal (bullish crossover)
            cross_down        - MACD crossed below signal (bearish crossover)
            above_zero        - MACD line > 0
            below_zero        - MACD line < 0
            histogram_positive - histogram > 0
            histogram_negative - histogram < 0
            histogram_rising  - histogram increasing
            histogram_falling - histogram decreasing
        """
        macd = state.get("current_macd")
        signal = state.get("current_signal")
        hist = state.get("current_histogram")
        prev_macd = state.get("prev_macd")
        prev_signal = state.get("prev_signal")
        prev_hist = state.get("prev_histogram")

        if operator == "cross_up":
            if None in (macd, signal, prev_macd, prev_signal):
                return False
            return prev_macd <= prev_signal and macd > signal

        if operator == "cross_down":
            if None in (macd, signal, prev_macd, prev_signal):
                return False
            return prev_macd >= prev_signal and macd < signal

        if operator == "above_zero":
            return macd is not None and macd > 0.0

        if operator == "below_zero":
            return macd is not None and macd < 0.0

        if operator == "histogram_positive":
            return hist is not None and hist > 0.0

        if operator == "histogram_negative":
            return hist is not None and hist < 0.0

        if operator == "histogram_rising":
            if hist is None or prev_hist is None:
                return False
            return hist > prev_hist

        if operator == "histogram_falling":
            if hist is None or prev_hist is None:
                return False
            return hist < prev_hist

        raise ValueError(f"Unknown MACD operator: {operator!r}")
