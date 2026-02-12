"""Fair Value Gap (FVG) detector.

Identifies gaps in price action caused by aggressive buying or
selling.  A bullish FVG occurs when candle[i-2].high < candle[i].low,
leaving a gap that price tends to revisit.  A bearish FVG is the
inverse: candle[i-2].low > candle[i].high.

The middle candle (candle[i-1]) is the impulse candle that creates
the gap.  Popular in ICT (Inner Circle Trader) methodology.

Operators supported:
    in_bullish_fvg   - price is inside a bullish FVG zone
    in_bearish_fvg   - price is inside a bearish FVG zone
    near_bullish_fvg - price approaching a bullish FVG
    near_bearish_fvg - price approaching a bearish FVG
    fresh_bullish    - unmitigated bullish FVG exists
    fresh_bearish    - unmitigated bearish FVG exists
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class FairValueGap(BaseIndicator):
    name = "Fair Value Gap"
    key = "fair_value_gap"
    category = "special"
    default_params = {
        "lookback": 50,
        "min_gap_pct": 0.05,
        "proximity_pct": 0.1,
        "max_gaps": 10,
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Detect Fair Value Gaps in a full candle history.

        A bullish FVG: candle[i-2].high < candle[i].low (gap up)
        A bearish FVG: candle[i-2].low > candle[i].high (gap down)

        Returns:
            bullish_fvgs - list of FVG dicts {top, bottom, index, mitigated}
            bearish_fvgs - list of FVG dicts {top, bottom, index, mitigated}
            current_price - latest close price
        """
        p = self.merge_params(params)
        min_gap_pct: float = p["min_gap_pct"]
        max_gaps: int = p["max_gaps"]

        n = len(candles)
        bullish_fvgs: list[dict[str, Any]] = []
        bearish_fvgs: list[dict[str, Any]] = []

        if n < 3:
            return self._build_state(bullish_fvgs, bearish_fvgs, candles)

        for i in range(2, n):
            c0 = candles[i - 2]  # Two candles ago
            c2 = candles[i]      # Current candle

            # Bullish FVG: gap between c0.high and c2.low
            if c2.low > c0.high:
                gap_size = c2.low - c0.high
                mid_price = (c2.low + c0.high) / 2.0
                gap_pct = (gap_size / mid_price * 100.0) if mid_price > 0 else 0.0

                if gap_pct >= min_gap_pct:
                    bullish_fvgs.append({
                        "top": c2.low,      # Top of gap zone
                        "bottom": c0.high,  # Bottom of gap zone
                        "index": i,
                        "mitigated": False,
                    })

            # Bearish FVG: gap between c0.low and c2.high
            if c0.low > c2.high:
                gap_size = c0.low - c2.high
                mid_price = (c0.low + c2.high) / 2.0
                gap_pct = (gap_size / mid_price * 100.0) if mid_price > 0 else 0.0

                if gap_pct >= min_gap_pct:
                    bearish_fvgs.append({
                        "top": c0.low,      # Top of gap zone
                        "bottom": c2.high,  # Bottom of gap zone
                        "index": i,
                        "mitigated": False,
                    })

        # Check mitigation
        for fvg in bullish_fvgs:
            # Bullish FVG mitigated when price drops into the gap
            for j in range(fvg["index"] + 1, n):
                if candles[j].low <= fvg["bottom"]:
                    fvg["mitigated"] = True
                    break

        for fvg in bearish_fvgs:
            # Bearish FVG mitigated when price rises into the gap
            for j in range(fvg["index"] + 1, n):
                if candles[j].high >= fvg["top"]:
                    fvg["mitigated"] = True
                    break

        # Keep only recent gaps
        bullish_fvgs = bullish_fvgs[-max_gaps:]
        bearish_fvgs = bearish_fvgs[-max_gaps:]

        return self._build_state(bullish_fvgs, bearish_fvgs, candles)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally detect new FVGs with one new candle."""
        p = self.merge_params(params)
        min_gap_pct: float = p["min_gap_pct"]
        max_gaps: int = p["max_gaps"]

        state["_candles"].append(candle)
        candles = state["_candles"]
        n = len(candles)
        state["current_price"] = candle.close

        # Check for new FVGs (need at least 3 candles)
        if n >= 3:
            c0 = candles[-3]
            c2 = candles[-1]

            # Bullish FVG
            if c2.low > c0.high:
                gap_size = c2.low - c0.high
                mid_price = (c2.low + c0.high) / 2.0
                gap_pct = (gap_size / mid_price * 100.0) if mid_price > 0 else 0.0

                if gap_pct >= min_gap_pct:
                    state["bullish_fvgs"].append({
                        "top": c2.low,
                        "bottom": c0.high,
                        "index": n - 1,
                        "mitigated": False,
                    })

            # Bearish FVG
            if c0.low > c2.high:
                gap_size = c0.low - c2.high
                mid_price = (c0.low + c2.high) / 2.0
                gap_pct = (gap_size / mid_price * 100.0) if mid_price > 0 else 0.0

                if gap_pct >= min_gap_pct:
                    state["bearish_fvgs"].append({
                        "top": c0.low,
                        "bottom": c2.high,
                        "index": n - 1,
                        "mitigated": False,
                    })

        # Update mitigation
        for fvg in state["bullish_fvgs"]:
            if not fvg["mitigated"] and candle.low <= fvg["bottom"]:
                fvg["mitigated"] = True

        for fvg in state["bearish_fvgs"]:
            if not fvg["mitigated"] and candle.high >= fvg["top"]:
                fvg["mitigated"] = True

        # Trim
        state["bullish_fvgs"] = state["bullish_fvgs"][-max_gaps:]
        state["bearish_fvgs"] = state["bearish_fvgs"][-max_gaps:]

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current FVG state."""
        price = state.get("current_price")
        bullish_fvgs = state.get("bullish_fvgs", [])
        bearish_fvgs = state.get("bearish_fvgs", [])
        proximity_pct = float(value) if value is not None else 0.1

        fresh_bullish = [f for f in bullish_fvgs if not f["mitigated"]]
        fresh_bearish = [f for f in bearish_fvgs if not f["mitigated"]]

        if operator == "in_bullish_fvg":
            if price is None:
                return False
            return any(f["bottom"] <= price <= f["top"] for f in fresh_bullish)

        elif operator == "in_bearish_fvg":
            if price is None:
                return False
            return any(f["bottom"] <= price <= f["top"] for f in fresh_bearish)

        elif operator == "near_bullish_fvg":
            if price is None:
                return False
            for f in fresh_bullish:
                mid = (f["top"] + f["bottom"]) / 2.0
                if mid > 0:
                    dist = abs(price - mid) / mid * 100.0
                    if dist <= proximity_pct:
                        return True
            return False

        elif operator == "near_bearish_fvg":
            if price is None:
                return False
            for f in fresh_bearish:
                mid = (f["top"] + f["bottom"]) / 2.0
                if mid > 0:
                    dist = abs(price - mid) / mid * 100.0
                    if dist <= proximity_pct:
                        return True
            return False

        elif operator == "fresh_bullish":
            return len(fresh_bullish) > 0

        elif operator == "fresh_bearish":
            return len(fresh_bearish) > 0

        else:
            raise ValueError(f"Unknown operator for FVG: {operator!r}")

    @staticmethod
    def _build_state(
        bullish_fvgs: list, bearish_fvgs: list, candles: list[Candle],
    ) -> dict[str, Any]:
        return {
            "bullish_fvgs": bullish_fvgs,
            "bearish_fvgs": bearish_fvgs,
            "current_price": candles[-1].close if candles else None,
            "_candles": list(candles),
        }
