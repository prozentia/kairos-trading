"""Ichimoku Cloud (Ichimoku Kinko Hyo).

A comprehensive indicator providing support/resistance, trend
direction, and momentum in one view.  Consists of five lines:
Tenkan-sen, Kijun-sen, Senkou Span A/B (the cloud), and Chikou Span.

Operators supported:
    above_cloud   - price is above both Senkou Span A and B
    below_cloud   - price is below both Senkou Span A and B
    in_cloud      - price is inside the cloud
    tk_cross_up   - Tenkan crossed above Kijun (bullish)
    tk_cross_down - Tenkan crossed below Kijun (bearish)
    cloud_green   - Senkou A > Senkou B (bullish cloud)
    cloud_red     - Senkou A < Senkou B (bearish cloud)
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


def _donchian_mid(candles: list[Candle], start: int, end: int) -> float:
    """Compute (highest high + lowest low) / 2 in the given range [start, end)."""
    high = max(candles[i].high for i in range(start, end))
    low = min(candles[i].low for i in range(start, end))
    return (high + low) / 2.0


@register
class Ichimoku(BaseIndicator):
    name = "Ichimoku Cloud"
    key = "ichimoku"
    category = "trend"
    default_params = {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26}

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute Ichimoku Cloud over a full candle history.

        Returns:
            tenkan_sen  - list of Tenkan-sen values (None if not enough data)
            kijun_sen   - list of Kijun-sen values
            senkou_a    - list of Senkou Span A (displaced forward by *displacement*)
            senkou_b    - list of Senkou Span B (displaced forward)
            chikou_span - list of Chikou Span (close displaced backwards)
            current_close - close of the last candle

        Note: senkou_a and senkou_b are indexed to match the *current*
        candle (i.e. the value at index i is the cloud value applicable
        at candle i, which was calculated *displacement* candles ago).
        This makes evaluate() straightforward.
        """
        p = self.merge_params(params)
        tenkan_p: int = p["tenkan"]
        kijun_p: int = p["kijun"]
        senkou_b_p: int = p["senkou_b"]
        displacement: int = p["displacement"]

        n = len(candles)

        tenkan: list[float | None] = [None] * n
        kijun: list[float | None] = [None] * n
        # senkou lines are also length n (some may be None at the edges)
        senkou_a: list[float | None] = [None] * n
        senkou_b: list[float | None] = [None] * n
        chikou: list[float | None] = [None] * n

        # Tenkan-sen: (highest high + lowest low) / 2 over tenkan_p
        for i in range(tenkan_p - 1, n):
            tenkan[i] = _donchian_mid(candles, i - tenkan_p + 1, i + 1)

        # Kijun-sen: same over kijun_p
        for i in range(kijun_p - 1, n):
            kijun[i] = _donchian_mid(candles, i - kijun_p + 1, i + 1)

        # Senkou Span A: (tenkan + kijun) / 2, displaced forward
        # Calculated at index i, plotted at i + displacement
        # But we store it at the *plotted* index for easier evaluation
        for i in range(n):
            if tenkan[i] is not None and kijun[i] is not None:
                target = i + displacement
                if target < n:
                    senkou_a[target] = (tenkan[i] + kijun[i]) / 2.0

        # Senkou Span B: midpoint of highest/lowest over senkou_b_p, displaced
        for i in range(senkou_b_p - 1, n):
            mid = _donchian_mid(candles, i - senkou_b_p + 1, i + 1)
            target = i + displacement
            if target < n:
                senkou_b[target] = mid

        # Chikou Span: current close displaced backwards by *displacement*
        for i in range(displacement, n):
            chikou[i - displacement] = candles[i].close

        # Store the highs/lows window for incremental updates
        max_window = max(tenkan_p, kijun_p, senkou_b_p)
        if n >= max_window:
            highs = [c.high for c in candles[-max_window:]]
            lows = [c.low for c in candles[-max_window:]]
        else:
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]

        return {
            "tenkan_sen": tenkan,
            "kijun_sen": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
            "chikou_span": chikou,
            "tenkan_period": tenkan_p,
            "kijun_period": kijun_p,
            "senkou_b_period": senkou_b_p,
            "displacement": displacement,
            "_highs": highs,
            "_lows": lows,
            "current_close": candles[-1].close if candles else 0.0,
        }

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update Ichimoku with one new candle.

        For simplicity, this appends None for senkou lines (they
        require look-ahead displacement) and correctly computes
        tenkan/kijun from the stored high/low window.
        """
        p = self.merge_params(params)
        tenkan_p: int = p["tenkan"]
        kijun_p: int = p["kijun"]
        senkou_b_p: int = p["senkou_b"]

        tenkan_list: list[float | None] = state["tenkan_sen"]
        kijun_list: list[float | None] = state["kijun_sen"]
        senkou_a_list: list[float | None] = state["senkou_a"]
        senkou_b_list: list[float | None] = state["senkou_b"]
        chikou_list: list[float | None] = state["chikou_span"]

        # Maintain a window of highs and lows for tenkan/kijun/senkou_b
        highs: list[float] = state.get("_highs", [])
        lows: list[float] = state.get("_lows", [])
        highs.append(candle.high)
        lows.append(candle.low)

        # Keep only the largest window needed
        max_window = max(tenkan_p, kijun_p, senkou_b_p)
        if len(highs) > max_window:
            highs = highs[-max_window:]
            lows = lows[-max_window:]

        # Tenkan
        if len(highs) >= tenkan_p:
            h = max(highs[-tenkan_p:])
            lo = min(lows[-tenkan_p:])
            tenkan_list.append((h + lo) / 2.0)
        else:
            tenkan_list.append(None)

        # Kijun
        if len(highs) >= kijun_p:
            h = max(highs[-kijun_p:])
            lo = min(lows[-kijun_p:])
            kijun_list.append((h + lo) / 2.0)
        else:
            kijun_list.append(None)

        # Senkou lines: cannot compute for "current" index without future data
        senkou_a_list.append(None)
        senkou_b_list.append(None)

        # Chikou: place current close *displacement* candles back
        # We cannot overwrite past indices easily, so append None
        chikou_list.append(None)

        state["_highs"] = highs
        state["_lows"] = lows
        state["current_close"] = candle.close
        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate Ichimoku conditions.

        Supported: above_cloud, below_cloud, in_cloud,
                   tk_cross_up, tk_cross_down, cloud_green, cloud_red.
        """
        tenkan = state.get("tenkan_sen", [])
        kijun = state.get("kijun_sen", [])
        senkou_a = state.get("senkou_a", [])
        senkou_b = state.get("senkou_b", [])
        current_close: float = state.get("current_close", 0.0)

        if operator == "above_cloud":
            sa = _last_valid(senkou_a)
            sb = _last_valid(senkou_b)
            if sa is None or sb is None:
                return False
            cloud_top = max(sa, sb)
            return current_close > cloud_top

        elif operator == "below_cloud":
            sa = _last_valid(senkou_a)
            sb = _last_valid(senkou_b)
            if sa is None or sb is None:
                return False
            cloud_bottom = min(sa, sb)
            return current_close < cloud_bottom

        elif operator == "in_cloud":
            sa = _last_valid(senkou_a)
            sb = _last_valid(senkou_b)
            if sa is None or sb is None:
                return False
            cloud_top = max(sa, sb)
            cloud_bottom = min(sa, sb)
            return cloud_bottom <= current_close <= cloud_top

        elif operator == "tk_cross_up":
            return _detect_cross(tenkan, kijun, direction="up")

        elif operator == "tk_cross_down":
            return _detect_cross(tenkan, kijun, direction="down")

        elif operator == "cloud_green":
            sa = _last_valid(senkou_a)
            sb = _last_valid(senkou_b)
            if sa is None or sb is None:
                return False
            return sa > sb

        elif operator == "cloud_red":
            sa = _last_valid(senkou_a)
            sb = _last_valid(senkou_b)
            if sa is None or sb is None:
                return False
            return sa < sb

        else:
            raise ValueError(f"Unknown operator for Ichimoku: {operator!r}")


def _last_valid(values: list[float | None]) -> float | None:
    for v in reversed(values):
        if v is not None:
            return v
    return None


def _detect_cross(
    line_a: list[float | None],
    line_b: list[float | None],
    direction: str,
) -> bool:
    """Detect if line_a just crossed line_b in the given direction.

    direction='up'  -> line_a crossed above line_b
    direction='down' -> line_a crossed below line_b
    """
    # Find last two indices where both are valid
    n = min(len(line_a), len(line_b))
    cur_idx = None
    for i in range(n - 1, -1, -1):
        if line_a[i] is not None and line_b[i] is not None:
            cur_idx = i
            break
    if cur_idx is None or cur_idx < 1:
        return False

    prev_idx = None
    for i in range(cur_idx - 1, -1, -1):
        if line_a[i] is not None and line_b[i] is not None:
            prev_idx = i
            break
    if prev_idx is None:
        return False

    a_cur, b_cur = line_a[cur_idx], line_b[cur_idx]
    a_prev, b_prev = line_a[prev_idx], line_b[prev_idx]

    if direction == "up":
        return a_prev <= b_prev and a_cur > b_cur  # type: ignore[operator]
    else:
        return a_prev >= b_prev and a_cur < b_cur  # type: ignore[operator]
