"""Order Block detector.

Identifies institutional order blocks -- zones where large players
have placed significant orders, creating supply/demand imbalances.
A bullish order block is the last bearish candle before a strong
bullish move; a bearish order block is the last bullish candle before
a strong bearish move.

Algorithm:
    1. Scan candles for impulsive moves (large body > min_impulse_pct).
    2. The last opposing candle before the impulsive move is the OB.
    3. Bullish OB: last red candle before a big green impulse.
    4. Bearish OB: last green candle before a big red impulse.
    5. An OB is "mitigated" when price returns to it (fills the zone).
    6. Only unmitigated (fresh) OBs are considered active.

Operators supported:
    in_bullish_ob   - price is inside a bullish order block zone
    in_bearish_ob   - price is inside a bearish order block zone
    near_bullish_ob - price is approaching a bullish OB (within pct)
    near_bearish_ob - price is approaching a bearish OB (within pct)
    fresh_bullish   - unmitigated bullish OB detected
    fresh_bearish   - unmitigated bearish OB detected
"""

from __future__ import annotations

from typing import Any

from core.indicators.base import BaseIndicator
from core.indicators.registry import register
from core.models import Candle


@register
class OrderBlock(BaseIndicator):
    name = "Order Block"
    key = "order_block"
    category = "special"
    default_params = {
        "lookback": 20,
        "min_impulse_pct": 0.5,
        "proximity_pct": 0.1,
        "max_blocks": 5,
    }

    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Detect order blocks in a full candle history.

        Returns:
            bullish_obs  - list of bullish OB dicts {high, low, index, mitigated}
            bearish_obs  - list of bearish OB dicts {high, low, index, mitigated}
            current_price - latest close price
        """
        p = self.merge_params(params)
        min_impulse_pct: float = p["min_impulse_pct"]
        max_blocks: int = p["max_blocks"]

        n = len(candles)
        bullish_obs: list[dict[str, Any]] = []
        bearish_obs: list[dict[str, Any]] = []

        if n < 2:
            return self._build_state(bullish_obs, bearish_obs, candles)

        for i in range(1, n):
            body_pct = _body_pct(candles[i])

            if body_pct >= min_impulse_pct:
                is_bullish_impulse = candles[i].close > candles[i].open
                is_bearish_impulse = candles[i].close < candles[i].open

                if is_bullish_impulse:
                    # Look for the last bearish candle before this impulse
                    ob_candle = _find_last_opposing(candles, i, bearish=True)
                    if ob_candle is not None:
                        ob_idx, ob_c = ob_candle
                        ob = {
                            "high": ob_c.high,
                            "low": ob_c.low,
                            "index": ob_idx,
                            "mitigated": False,
                        }
                        bullish_obs.append(ob)

                elif is_bearish_impulse:
                    # Look for the last bullish candle before this impulse
                    ob_candle = _find_last_opposing(candles, i, bearish=False)
                    if ob_candle is not None:
                        ob_idx, ob_c = ob_candle
                        ob = {
                            "high": ob_c.high,
                            "low": ob_c.low,
                            "index": ob_idx,
                            "mitigated": False,
                        }
                        bearish_obs.append(ob)

        # Check for mitigation: price returned to the OB zone
        if n > 0:
            current_price = candles[-1].close
            for ob in bullish_obs:
                # Bullish OB mitigated when price drops below its low
                for j in range(ob["index"] + 1, n):
                    if candles[j].low <= ob["low"]:
                        ob["mitigated"] = True
                        break

            for ob in bearish_obs:
                # Bearish OB mitigated when price rises above its high
                for j in range(ob["index"] + 1, n):
                    if candles[j].high >= ob["high"]:
                        ob["mitigated"] = True
                        break

        # Keep only the most recent blocks
        bullish_obs = bullish_obs[-max_blocks:]
        bearish_obs = bearish_obs[-max_blocks:]

        return self._build_state(bullish_obs, bearish_obs, candles)

    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update order blocks with one new candle."""
        p = self.merge_params(params)
        min_impulse_pct: float = p["min_impulse_pct"]
        max_blocks: int = p["max_blocks"]

        state["_candles"].append(candle)
        candles = state["_candles"]
        n = len(candles)
        state["current_price"] = candle.close

        if n < 2:
            return state

        # Check if the new candle creates an impulsive move
        body_pct = _body_pct(candle)
        if body_pct >= min_impulse_pct:
            is_bullish = candle.close > candle.open
            is_bearish = candle.close < candle.open

            if is_bullish:
                ob_candle = _find_last_opposing(candles, n - 1, bearish=True)
                if ob_candle is not None:
                    ob_idx, ob_c = ob_candle
                    state["bullish_obs"].append({
                        "high": ob_c.high,
                        "low": ob_c.low,
                        "index": ob_idx,
                        "mitigated": False,
                    })

            elif is_bearish:
                ob_candle = _find_last_opposing(candles, n - 1, bearish=False)
                if ob_candle is not None:
                    ob_idx, ob_c = ob_candle
                    state["bearish_obs"].append({
                        "high": ob_c.high,
                        "low": ob_c.low,
                        "index": ob_idx,
                        "mitigated": False,
                    })

        # Update mitigation status
        for ob in state["bullish_obs"]:
            if not ob["mitigated"] and candle.low <= ob["low"]:
                ob["mitigated"] = True

        for ob in state["bearish_obs"]:
            if not ob["mitigated"] and candle.high >= ob["high"]:
                ob["mitigated"] = True

        # Trim to max_blocks
        state["bullish_obs"] = state["bullish_obs"][-max_blocks:]
        state["bearish_obs"] = state["bearish_obs"][-max_blocks:]

        return state

    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current order block state."""
        price = state.get("current_price")
        bullish_obs = state.get("bullish_obs", [])
        bearish_obs = state.get("bearish_obs", [])
        proximity_pct = float(value) if value is not None else 0.1

        fresh_bullish = [ob for ob in bullish_obs if not ob["mitigated"]]
        fresh_bearish = [ob for ob in bearish_obs if not ob["mitigated"]]

        if operator == "in_bullish_ob":
            if price is None:
                return False
            return any(ob["low"] <= price <= ob["high"] for ob in fresh_bullish)

        elif operator == "in_bearish_ob":
            if price is None:
                return False
            return any(ob["low"] <= price <= ob["high"] for ob in fresh_bearish)

        elif operator == "near_bullish_ob":
            if price is None:
                return False
            for ob in fresh_bullish:
                mid = (ob["high"] + ob["low"]) / 2.0
                if mid > 0:
                    dist = abs(price - mid) / mid * 100.0
                    if dist <= proximity_pct:
                        return True
            return False

        elif operator == "near_bearish_ob":
            if price is None:
                return False
            for ob in fresh_bearish:
                mid = (ob["high"] + ob["low"]) / 2.0
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
            raise ValueError(f"Unknown operator for Order Block: {operator!r}")

    @staticmethod
    def _build_state(
        bullish_obs: list, bearish_obs: list, candles: list[Candle],
    ) -> dict[str, Any]:
        return {
            "bullish_obs": bullish_obs,
            "bearish_obs": bearish_obs,
            "current_price": candles[-1].close if candles else None,
            "_candles": list(candles),
        }


def _body_pct(candle: Candle) -> float:
    """Compute the body size as a percentage of the candle price."""
    mid = (candle.open + candle.close) / 2.0
    if mid == 0:
        return 0.0
    return abs(candle.close - candle.open) / mid * 100.0


def _find_last_opposing(
    candles: list[Candle], impulse_idx: int, bearish: bool,
) -> tuple[int, Candle] | None:
    """Find the last opposing candle before an impulsive move.

    If bearish=True, look for last bearish (red) candle.
    If bearish=False, look for last bullish (green) candle.
    """
    for i in range(impulse_idx - 1, max(impulse_idx - 10, -1), -1):
        c = candles[i]
        if bearish and c.close < c.open:
            return (i, c)
        elif not bearish and c.close > c.open:
            return (i, c)
    return None
