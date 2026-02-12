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
        """Compute ADX, +DI, -DI over a full candle history.

        Uses Wilder's smoothing (same as original ADX definition).

        Returns:
            adx     - list of ADX values (None until 2*period)
            plus_di - list of +DI values (None until period)
            minus_di- list of -DI values
            period  - period used
            current_close - close of last candle
        """
        p = self.merge_params(params)
        period: int = p["period"]
        n = len(candles)

        adx_values: list[float | None] = [None] * n
        plus_di_values: list[float | None] = [None] * n
        minus_di_values: list[float | None] = [None] * n

        # Need at least 2*period + 1 candles for a meaningful ADX
        if n < 2:
            return self._build_state(
                adx_values, plus_di_values, minus_di_values, period, candles
            )

        # Step 1: Compute raw +DM, -DM, TR for each candle (from index 1)
        plus_dm: list[float] = [0.0] * n
        minus_dm: list[float] = [0.0] * n
        tr: list[float] = [0.0] * n

        for i in range(1, n):
            high_diff = candles[i].high - candles[i - 1].high
            low_diff = candles[i - 1].low - candles[i].low

            plus_dm[i] = high_diff if (high_diff > low_diff and high_diff > 0) else 0.0
            minus_dm[i] = low_diff if (low_diff > high_diff and low_diff > 0) else 0.0

            hl = candles[i].high - candles[i].low
            hc = abs(candles[i].high - candles[i - 1].close)
            lc = abs(candles[i].low - candles[i - 1].close)
            tr[i] = max(hl, hc, lc)

        if n < period + 1:
            return self._build_state(
                adx_values, plus_di_values, minus_di_values, period, candles
            )

        # Step 2: First smoothed values (sum of first *period* values, starting at index 1)
        sm_plus_dm = sum(plus_dm[1 : period + 1])
        sm_minus_dm = sum(minus_dm[1 : period + 1])
        sm_tr = sum(tr[1 : period + 1])

        # First +DI / -DI at index = period
        if sm_tr > 0:
            plus_di_values[period] = 100.0 * sm_plus_dm / sm_tr
            minus_di_values[period] = 100.0 * sm_minus_dm / sm_tr
        else:
            plus_di_values[period] = 0.0
            minus_di_values[period] = 0.0

        # Step 3: Wilder-smooth and compute DI for subsequent candles
        dx_list: list[float] = []

        pdi = plus_di_values[period]
        mdi = minus_di_values[period]
        if pdi is not None and mdi is not None:
            di_sum = pdi + mdi
            dx_list.append(100.0 * abs(pdi - mdi) / di_sum if di_sum > 0 else 0.0)

        for i in range(period + 1, n):
            sm_plus_dm = sm_plus_dm - (sm_plus_dm / period) + plus_dm[i]
            sm_minus_dm = sm_minus_dm - (sm_minus_dm / period) + minus_dm[i]
            sm_tr = sm_tr - (sm_tr / period) + tr[i]

            if sm_tr > 0:
                pdi_val = 100.0 * sm_plus_dm / sm_tr
                mdi_val = 100.0 * sm_minus_dm / sm_tr
            else:
                pdi_val = 0.0
                mdi_val = 0.0

            plus_di_values[i] = pdi_val
            minus_di_values[i] = mdi_val

            di_sum = pdi_val + mdi_val
            dx = 100.0 * abs(pdi_val - mdi_val) / di_sum if di_sum > 0 else 0.0
            dx_list.append(dx)

        # Step 4: Compute ADX (smoothed DX)
        # First ADX = SMA of first *period* DX values
        if len(dx_list) >= period:
            first_adx = sum(dx_list[:period]) / period
            # The first ADX corresponds to index = period + period = 2 * period
            adx_idx = 2 * period
            if adx_idx < n:
                adx_values[adx_idx] = first_adx

            prev_adx = first_adx
            for j in range(period, len(dx_list)):
                adx_idx = period + 1 + j  # offset by period+1 (start of dx_list)
                if adx_idx < n:
                    new_adx = (prev_adx * (period - 1) + dx_list[j]) / period
                    adx_values[adx_idx] = new_adx
                    prev_adx = new_adx

        return self._build_state(
            adx_values, plus_di_values, minus_di_values, period, candles,
            _sm_plus_dm=sm_plus_dm, _sm_minus_dm=sm_minus_dm, _sm_tr=sm_tr,
            _prev_adx=_last_valid_float(adx_values),
        )

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update ADX/DMI with one new candle."""
        p = self.merge_params(params)
        period: int = p["period"]

        adx_list: list[float | None] = state["adx"]
        pdi_list: list[float | None] = state["plus_di"]
        mdi_list: list[float | None] = state["minus_di"]

        prev_close = state.get("current_close", candle.close)
        sm_plus_dm: float | None = state.get("_sm_plus_dm")
        sm_minus_dm: float | None = state.get("_sm_minus_dm")
        sm_tr: float | None = state.get("_sm_tr")
        prev_adx: float | None = state.get("_prev_adx")
        prev_high: float = state.get("_prev_high", candle.high)

        if sm_plus_dm is None or sm_minus_dm is None or sm_tr is None:
            adx_list.append(None)
            pdi_list.append(None)
            mdi_list.append(None)
            state["current_close"] = candle.close
            state["_prev_high"] = candle.high
            state["_prev_low"] = candle.low
            return state

        # Raw +DM, -DM, TR
        prev_low = state.get("_prev_low", candle.low)
        high_diff = candle.high - prev_high
        low_diff = prev_low - candle.low

        pdm = high_diff if (high_diff > low_diff and high_diff > 0) else 0.0
        mdm = low_diff if (low_diff > high_diff and low_diff > 0) else 0.0

        hl = candle.high - candle.low
        hc = abs(candle.high - prev_close)
        lc = abs(candle.low - prev_close)
        true_range = max(hl, hc, lc)

        # Wilder smooth
        sm_plus_dm = sm_plus_dm - (sm_plus_dm / period) + pdm
        sm_minus_dm = sm_minus_dm - (sm_minus_dm / period) + mdm
        sm_tr = sm_tr - (sm_tr / period) + true_range

        if sm_tr > 0:
            pdi_val = 100.0 * sm_plus_dm / sm_tr
            mdi_val = 100.0 * sm_minus_dm / sm_tr
        else:
            pdi_val = 0.0
            mdi_val = 0.0

        pdi_list.append(pdi_val)
        mdi_list.append(mdi_val)

        # ADX
        di_sum = pdi_val + mdi_val
        dx = 100.0 * abs(pdi_val - mdi_val) / di_sum if di_sum > 0 else 0.0
        if prev_adx is not None:
            new_adx = (prev_adx * (period - 1) + dx) / period
            adx_list.append(new_adx)
            state["_prev_adx"] = new_adx
        else:
            adx_list.append(None)

        state["_sm_plus_dm"] = sm_plus_dm
        state["_sm_minus_dm"] = sm_minus_dm
        state["_sm_tr"] = sm_tr
        state["_prev_high"] = candle.high
        state["_prev_low"] = candle.low
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate ADX/DMI conditions.

        Supported: trending, not_trending, bullish, bearish,
                   di_cross_up, di_cross_down.
        """
        adx_list: list[float | None] = state.get("adx", [])
        pdi_list: list[float | None] = state.get("plus_di", [])
        mdi_list: list[float | None] = state.get("minus_di", [])

        if operator == "trending":
            threshold = value if value is not None else 25.0
            adx = _last_valid_float(adx_list)
            return adx is not None and adx > threshold

        elif operator == "not_trending":
            threshold = value if value is not None else 20.0
            adx = _last_valid_float(adx_list)
            return adx is not None and adx < threshold

        elif operator == "bullish":
            pdi = _last_valid_float(pdi_list)
            mdi = _last_valid_float(mdi_list)
            return pdi is not None and mdi is not None and pdi > mdi

        elif operator == "bearish":
            pdi = _last_valid_float(pdi_list)
            mdi = _last_valid_float(mdi_list)
            return pdi is not None and mdi is not None and mdi > pdi

        elif operator == "di_cross_up":
            return _detect_di_cross(pdi_list, mdi_list, direction="up")

        elif operator == "di_cross_down":
            return _detect_di_cross(pdi_list, mdi_list, direction="down")

        else:
            raise ValueError(f"Unknown operator for ADX/DMI: {operator!r}")

    @staticmethod
    def _build_state(
        adx: list, plus_di: list, minus_di: list,
        period: int, candles: list[Candle],
        _sm_plus_dm: float | None = None,
        _sm_minus_dm: float | None = None,
        _sm_tr: float | None = None,
        _prev_adx: float | None = None,
    ) -> dict[str, Any]:
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "period": period,
            "_sm_plus_dm": _sm_plus_dm,
            "_sm_minus_dm": _sm_minus_dm,
            "_sm_tr": _sm_tr,
            "_prev_adx": _prev_adx,
            "_prev_high": candles[-1].high if candles else 0.0,
            "_prev_low": candles[-1].low if candles else 0.0,
            "current_close": candles[-1].close if candles else 0.0,
        }


def _last_valid_float(values: list[float | None]) -> float | None:
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _detect_di_cross(
    pdi: list[float | None],
    mdi: list[float | None],
    direction: str,
) -> bool:
    """Detect if +DI just crossed -DI."""
    n = min(len(pdi), len(mdi))
    cur_idx = None
    for i in range(n - 1, -1, -1):
        if pdi[i] is not None and mdi[i] is not None:
            cur_idx = i
            break
    if cur_idx is None or cur_idx < 1:
        return False

    prev_idx = None
    for i in range(cur_idx - 1, -1, -1):
        if pdi[i] is not None and mdi[i] is not None:
            prev_idx = i
            break
    if prev_idx is None:
        return False

    p_cur, m_cur = pdi[cur_idx], mdi[cur_idx]
    p_prev, m_prev = pdi[prev_idx], mdi[prev_idx]

    if direction == "up":
        return p_prev <= m_prev and p_cur > m_cur  # type: ignore[operator]
    else:
        return m_prev <= p_prev and m_cur > p_cur  # type: ignore[operator]
