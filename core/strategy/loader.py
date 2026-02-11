"""Strategy loader -- parses and validates JSON strategy definitions.

Converts a raw dict (from JSON) into a StrategyConfig dataclass and
runs structural validation to catch misconfiguration early.
"""

from __future__ import annotations

from typing import Any

from core.indicators.registry import get_registry
from core.models import StrategyConfig


class StrategyLoader:
    """Load and validate strategy configurations."""

    def load_from_dict(self, data: dict[str, Any]) -> StrategyConfig:
        """Parse a raw dict into a StrategyConfig.

        Args:
            data: Dict typically deserialized from JSON.

        Returns:
            A populated StrategyConfig instance.
        """
        config = StrategyConfig.from_dict(data)

        # Auto-detect which indicators the strategy needs.
        if not config.indicators_needed:
            config.indicators_needed = self._extract_indicators(config)

        return config

    def validate(self, config: StrategyConfig) -> list[str]:
        """Validate a StrategyConfig and return a list of error messages.

        An empty list means the configuration is valid.

        Checks performed:
            - Name is non-empty.
            - At least one pair is defined.
            - Entry conditions are present and structurally valid.
            - All referenced indicators are registered.
            - Risk parameters are within sane bounds.
        """
        errors: list[str] = []

        if not config.name:
            errors.append("Strategy must have a non-empty 'name'.")

        if not config.pairs:
            errors.append("Strategy must define at least one trading pair.")

        if not config.entry_conditions:
            errors.append("Strategy must define 'entry_conditions'.")

        # Validate all referenced indicators exist in the registry.
        registry = get_registry()
        for key in config.indicators_needed:
            if key not in registry:
                errors.append(f"Unknown indicator referenced: {key!r}.")

        # Validate condition tree structure.
        for label, tree in [
            ("entry_conditions", config.entry_conditions),
            ("exit_conditions", config.exit_conditions),
        ]:
            if tree:
                tree_errors = self._validate_condition_tree(tree, label)
                errors.extend(tree_errors)

        # Validate risk parameters.
        risk = config.risk
        if risk:
            if risk.get("stop_loss_pct", 0) < 0:
                errors.append("stop_loss_pct must be >= 0.")
            if risk.get("trailing_activation_pct", 0) < 0:
                errors.append("trailing_activation_pct must be >= 0.")

        return errors

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_indicators(self, config: StrategyConfig) -> list[str]:
        """Walk the condition trees and collect all indicator keys."""
        keys: set[str] = set()
        for tree in (config.entry_conditions, config.exit_conditions):
            if tree:
                self._collect_indicator_keys(tree, keys)
        return sorted(keys)

    def _collect_indicator_keys(
        self, node: dict[str, Any], keys: set[str]
    ) -> None:
        """Recursively collect indicator keys from a condition tree."""
        if "indicator" in node:
            keys.add(node["indicator"])
        for child in node.get("conditions", []):
            self._collect_indicator_keys(child, keys)

    def _validate_condition_tree(
        self, node: dict[str, Any], path: str
    ) -> list[str]:
        """Recursively validate the structure of a condition tree."""
        errors: list[str] = []

        if "indicator" in node:
            # Leaf condition -- must have an operator.
            if "operator" not in node:
                errors.append(f"{path}: condition with indicator {node['indicator']!r} "
                              f"is missing 'operator'.")
        elif "logic" in node:
            logic = node["logic"].upper()
            if logic not in ("AND", "OR", "NOT"):
                errors.append(f"{path}: unknown logic operator {logic!r}.")
            children = node.get("conditions", [])
            if not children:
                errors.append(f"{path}: logic group {logic!r} has no conditions.")
            for i, child in enumerate(children):
                child_errors = self._validate_condition_tree(
                    child, f"{path}.conditions[{i}]"
                )
                errors.extend(child_errors)
        else:
            errors.append(f"{path}: node must have either 'indicator' or 'logic' key.")

        return errors
