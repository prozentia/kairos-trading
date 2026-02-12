"""True Strength Index (TSI).

A double-smoothed momentum oscillator that shows both the direction
and strength of a trend.  Uses double exponential smoothing of price
changes to filter noise.  Often paired with a signal line for
crossover entries.

Calculation:
    1. momentum = close - previous_close
    2. double_smoothed_momentum = EMA(EMA(momentum, long), short)
    3. double_smoothed_abs_momentum = EMA(EMA(|momentum|, long), short)
    4. TSI = (double_smoothed_momentum / double_smoothed_abs_momentum) * 100
    5. Signal = EMA(TSI, signal_period)

Operators supported:
    above_zero          - TSI > 0 (bullish momentum)
    below_zero          - TSI < 0 (bearish momentum)
    cross_up            - TSI crossed above signal line
    cross_down          - TSI crossed below signal line
    above               - TSI > value
    below               - TSI < value
    rising              - TSI is increasing
    falling             - TSI is decreasing
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _ema_multiplier(period: int) -> float:
    """EMA smoothing factor."""
    return 2.0 / (period + 1)


def _compute_ema_series(values: list[float], period: int) -> list[float | None]:
    """Compute full EMA series. First (period-1) entries are None."""
    n = len(values)
    result: list[float | None] = [None] * n
    if n < period:
        return result

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
class TSI(BaseIndicator):
    name = "True Strength Index"
    key = "tsi"
    category = "momentum"
    default_params = {"long_period": 25, "short_period": 13, "signal_period": 7}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute TSI over a full candle history.

        Returns dict with:
            tsi           - list of TSI values (None for warmup)
            signal        - list of signal line values
            prev_tsi      - previous TSI value
            prev_signal   - previous signal value
            current_tsi   - latest TSI value
            current_signal - latest signal value
            _ema state fields for incremental updates
        """
        p = self.merge_params(params)
        long_period: int = p["long_period"]
        short_period: int = p["short_period"]
        signal_period: int = p["signal_period"]

        n = len(candles)
        tsi_values: list[float | None] = [None] * n
        signal_values: list[float | None] = [None] * n

        if n < 2:
            return {
                "tsi": tsi_values,
                "signal": signal_values,
                "prev_tsi": None,
                "prev_signal": None,
                "current_tsi": None,
                "current_signal": None,
                "_last_close": candles[-1].close if n > 0 else None,
            }

        # Step 1: compute momentum (price change)
        momentum = [candles[i].close - candles[i - 1].close for i in range(1, n)]
        abs_momentum = [abs(m) for m in momentum]

        # Step 2: first EMA smoothing (long period)
        ema_long_mom = _compute_ema_series(momentum, long_period)
        ema_long_abs = _compute_ema_series(abs_momentum, long_period)

        # Step 3: second EMA smoothing (short period) on non-None values
        # Extract non-None values from first EMA
        ema_long_mom_clean: list[float] = []
        ema_long_mom_indices: list[int] = []
        for i, v in enumerate(ema_long_mom):
            if v is not None:
                ema_long_mom_clean.append(v)
                ema_long_mom_indices.append(i)

        ema_long_abs_clean: list[float] = []
        ema_long_abs_indices: list[int] = []
        for i, v in enumerate(ema_long_abs):
            if v is not None:
                ema_long_abs_clean.append(v)
                ema_long_abs_indices.append(i)

        double_smoothed_mom = _compute_ema_series(ema_long_mom_clean, short_period)
        double_smoothed_abs = _compute_ema_series(ema_long_abs_clean, short_period)

        # Step 4: compute TSI values
        # Map back to momentum indices (offset by 1 from candle indices)
        tsi_raw: list[float] = []
        tsi_raw_indices: list[int] = []

        for j in range(len(double_smoothed_mom)):
            ds_mom = double_smoothed_mom[j]
            ds_abs = double_smoothed_abs[j] if j < len(double_smoothed_abs) else None

            if ds_mom is not None and ds_abs is not None and ds_abs != 0.0:
                tsi_val = (ds_mom / ds_abs) * 100.0
                # Map back: momentum index j maps to ema_long_mom_indices[j]
                # which is a momentum index, which is candle index + 1
                if j < len(ema_long_mom_indices):
                    candle_idx = ema_long_mom_indices[j] + 1
                    if candle_idx < n:
                        tsi_values[candle_idx] = tsi_val
                        tsi_raw.append(tsi_val)
                        tsi_raw_indices.append(candle_idx)

        # Step 5: signal line = EMA of TSI
        if len(tsi_raw) >= signal_period:
            sig_ema = _compute_ema_series(tsi_raw, signal_period)
            for j, val in enumerate(sig_ema):
                if val is not None and j < len(tsi_raw_indices):
                    signal_values[tsi_raw_indices[j]] = val

        current_tsi = tsi_values[-1] if n > 0 else None
        current_signal = signal_values[-1] if n > 0 else None
        prev_tsi = tsi_values[-2] if n >= 2 else None
        prev_signal = signal_values[-2] if n >= 2 else None

        # Store EMA states for incremental updates
        # Last values of each EMA chain
        last_ema_long_mom = None
        for v in reversed(ema_long_mom):
            if v is not None:
                last_ema_long_mom = v
                break

        last_ema_long_abs = None
        for v in reversed(ema_long_abs):
            if v is not None:
                last_ema_long_abs = v
                break

        last_ds_mom = None
        for v in reversed(double_smoothed_mom):
            if v is not None:
                last_ds_mom = v
                break

        last_ds_abs = None
        for v in reversed(double_smoothed_abs):
            if v is not None:
                last_ds_abs = v
                break

        last_signal_ema = None
        for v in reversed(signal_values):
            if v is not None:
                last_signal_ema = v
                break

        return {
            "tsi": tsi_values,
            "signal": signal_values,
            "prev_tsi": prev_tsi,
            "prev_signal": prev_signal,
            "current_tsi": current_tsi,
            "current_signal": current_signal,
            "_last_close": candles[-1].close,
            "_ema_long_mom": last_ema_long_mom,
            "_ema_long_abs": last_ema_long_abs,
            "_ds_mom": last_ds_mom,
            "_ds_abs": last_ds_abs,
            "_signal_ema": last_signal_ema,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update TSI with one new candle."""
        p = self.merge_params(params)
        long_period: int = p["long_period"]
        short_period: int = p["short_period"]
        signal_period: int = p["signal_period"]

        last_close = state.get("_last_close")
        if last_close is None:
            state["_last_close"] = candle.close
            state["tsi"].append(None)
            state["signal"].append(None)
            return state

        mom = candle.close - last_close
        abs_mom = abs(mom)

        ema_long_mom = state.get("_ema_long_mom")
        ema_long_abs = state.get("_ema_long_abs")
        ds_mom = state.get("_ds_mom")
        ds_abs = state.get("_ds_abs")
        signal_ema = state.get("_signal_ema")

        # Update first EMA (long period)
        k_long = _ema_multiplier(long_period)
        if ema_long_mom is not None:
            new_ema_long_mom = mom * k_long + ema_long_mom * (1.0 - k_long)
            new_ema_long_abs = abs_mom * k_long + ema_long_abs * (1.0 - k_long)
        else:
            state["_last_close"] = candle.close
            state["tsi"].append(None)
            state["signal"].append(None)
            return state

        # Update second EMA (short period)
        k_short = _ema_multiplier(short_period)
        if ds_mom is not None:
            new_ds_mom = new_ema_long_mom * k_short + ds_mom * (1.0 - k_short)
            new_ds_abs = new_ema_long_abs * k_short + ds_abs * (1.0 - k_short)
        else:
            state["_ema_long_mom"] = new_ema_long_mom
            state["_ema_long_abs"] = new_ema_long_abs
            state["_last_close"] = candle.close
            state["tsi"].append(None)
            state["signal"].append(None)
            return state

        # Compute TSI
        new_tsi = None
        if new_ds_abs != 0.0:
            new_tsi = (new_ds_mom / new_ds_abs) * 100.0

        # Update signal EMA
        new_signal = None
        if new_tsi is not None and signal_ema is not None:
            k_sig = _ema_multiplier(signal_period)
            new_signal = new_tsi * k_sig + signal_ema * (1.0 - k_sig)

        state["prev_tsi"] = state.get("current_tsi")
        state["prev_signal"] = state.get("current_signal")
        state["current_tsi"] = new_tsi
        state["current_signal"] = new_signal

        state["_last_close"] = candle.close
        state["_ema_long_mom"] = new_ema_long_mom
        state["_ema_long_abs"] = new_ema_long_abs
        state["_ds_mom"] = new_ds_mom
        state["_ds_abs"] = new_ds_abs
        if new_signal is not None:
            state["_signal_ema"] = new_signal

        state["tsi"].append(new_tsi)
        state["signal"].append(new_signal)

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate TSI conditions.

        Supported operators:
            above_zero - TSI > 0
            below_zero - TSI < 0
            above      - TSI > value
            below      - TSI < value
            cross_up   - TSI crossed above signal line
            cross_down - TSI crossed below signal line
            rising     - TSI is increasing
            falling    - TSI is decreasing
        """
        current_tsi = state.get("current_tsi")
        current_signal = state.get("current_signal")
        prev_tsi = state.get("prev_tsi")
        prev_signal = state.get("prev_signal")

        if operator == "above_zero":
            return current_tsi is not None and current_tsi > 0.0

        if operator == "below_zero":
            return current_tsi is not None and current_tsi < 0.0

        if operator == "above":
            return current_tsi is not None and current_tsi > float(value)

        if operator == "below":
            return current_tsi is not None and current_tsi < float(value)

        if operator == "cross_up":
            if None in (current_tsi, current_signal, prev_tsi, prev_signal):
                return False
            return prev_tsi <= prev_signal and current_tsi > current_signal

        if operator == "cross_down":
            if None in (current_tsi, current_signal, prev_tsi, prev_signal):
                return False
            return prev_tsi >= prev_signal and current_tsi < current_signal

        if operator == "rising":
            if current_tsi is None or prev_tsi is None:
                return False
            return current_tsi > prev_tsi

        if operator == "falling":
            if current_tsi is None or prev_tsi is None:
                return False
            return current_tsi < prev_tsi

        raise ValueError(f"Unknown TSI operator: {operator!r}")
