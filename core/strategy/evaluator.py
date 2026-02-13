"""Strategy evaluator -- turns declarative JSON conditions into signals.

The evaluator walks the condition tree defined in a StrategyConfig and
checks each condition against the current indicator states.  Conditions
can be combined with AND / OR / NOT logic.

Condition JSON shape example::

    {
        "logic": "AND",
        "conditions": [
            {"indicator": "rsi", "operator": "below", "value": 30},
            {"indicator": "heikin_ashi", "operator": "is_green"},
            {
                "logic": "OR",
                "conditions": [
                    {"indicator": "bollinger", "operator": "touch_lower"},
                    {"indicator": "msb_glissant", "operator": "break_up"}
                ]
            }
        ]
    }
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.indicators.registry import get_registry
from core.models import Signal, SignalType, StrategyConfig


class StrategyEvaluator:
    """Evaluate a StrategyConfig against current indicator states."""

    def evaluate(
        self,
        strategy_config: StrategyConfig,
        indicator_states: dict[str, dict[str, Any]],
        context: dict[str, Any],
    ) -> Signal:
        """Run full evaluation: entry conditions, exit conditions, filters.

        Args:
            strategy_config: The parsed strategy definition.
            indicator_states: Mapping of indicator key -> current state dict.
            context: Runtime context (pair, price, timestamp, positions, etc.).

        Returns:
            A Signal (may be NO_SIGNAL if nothing triggers).
        """
        pair: str = context.get("pair", "")
        timeframe: str = context.get("timeframe", strategy_config.timeframe)
        price: float = context.get("price", 0.0)
        timestamp: datetime = context.get("timestamp", datetime.utcnow())
        has_position: bool = context.get("has_position", False)

        # Check exit conditions first (safety priority).
        if has_position and strategy_config.exit_conditions:
            exit_met = self._evaluate_group(
                strategy_config.exit_conditions, indicator_states, context
            )
            if exit_met:
                return Signal(
                    type=SignalType.SELL,
                    pair=pair,
                    timeframe=timeframe,
                    price=price,
                    timestamp=timestamp,
                    strategy_name=strategy_config.name,
                    reason="Exit conditions met",
                )

        # Check entry conditions only when no position is open.
        if not has_position and strategy_config.entry_conditions:
            entry_met = self._evaluate_group(
                strategy_config.entry_conditions, indicator_states, context
            )
            if entry_met:
                return Signal(
                    type=SignalType.BUY,
                    pair=pair,
                    timeframe=timeframe,
                    price=price,
                    timestamp=timestamp,
                    strategy_name=strategy_config.name,
                    reason="Entry conditions met",
                )

        return Signal(
            type=SignalType.NO_SIGNAL,
            pair=pair,
            timeframe=timeframe,
            price=price,
            timestamp=timestamp,
            strategy_name=strategy_config.name,
        )

    # ------------------------------------------------------------------
    # Recursive group evaluation
    # ------------------------------------------------------------------

    def _evaluate_group(
        self,
        group: dict[str, Any] | list[dict[str, Any]],
        states: dict[str, dict[str, Any]],
        context: dict[str, Any],
    ) -> bool:
        """Recursively evaluate a condition group (AND / OR / NOT).

        Args:
            group: A dict with "logic" and "conditions" keys, a single
                   condition dict with "indicator" / "operator", or a
                   flat list of conditions (treated as implicit AND).
            states: Current indicator states.
            context: Runtime context.

        Returns:
            True if the group evaluates to True.
        """
        # Flat list of conditions = implicit AND.
        if isinstance(group, list):
            if not group:
                return False
            return all(
                self._evaluate_group(c, states, context) for c in group
            )

        # Single condition (leaf node).
        if "indicator" in group:
            return self._evaluate_condition(group, states)

        logic: str = group.get("logic", "AND").upper()
        conditions: list[dict[str, Any]] = group.get("conditions", [])

        if not conditions:
            return False

        match logic:
            case "AND":
                return all(
                    self._evaluate_group(c, states, context) for c in conditions
                )
            case "OR":
                return any(
                    self._evaluate_group(c, states, context) for c in conditions
                )
            case "NOT":
                # NOT applies to the first condition only.
                return not self._evaluate_group(conditions[0], states, context)
            case _:
                raise ValueError(f"Unknown logic operator: {logic!r}")

    # ------------------------------------------------------------------
    # Single condition evaluation
    # ------------------------------------------------------------------

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        states: dict[str, dict[str, Any]],
    ) -> bool:
        """Evaluate a single indicator condition.

        Args:
            condition: Dict with keys "indicator", "operator", and
                       optionally "value" and "params".
            states: Current indicator states.

        Returns:
            True if the condition is satisfied.
        """
        indicator_key: str = condition["indicator"]
        operator: str = condition["operator"]
        value: Any = condition.get("value")

        registry = get_registry()
        indicator = registry.get(indicator_key)

        state = states.get(indicator_key)
        if state is None:
            # Indicator has not been computed yet -- cannot satisfy.
            return False

        return indicator.evaluate(state, operator, value)
