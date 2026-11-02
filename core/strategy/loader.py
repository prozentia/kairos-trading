"""Strategy loader -- parses and validates JSON strategy definitions.

Converts a raw dict (from JSON) into a StrategyConfig dataclass and
runs structural validation to catch misconfiguration early.
"""

from __future__ import annotations

import json
from typing import Any

from core.indicators.registry import get_registry
from core.models import StrategyConfig

# Condition params that are not indicator parameters. Multi-timeframe
# conditions are not supported yet: indicators always run on the strategy TF.
NON_INDICATOR_PARAMS = frozenset({"timeframe"})


def indicator_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Return the indicator parameters of a condition (non-indicator keys removed)."""
    if not params:
        return {}
    return {k: v for k, v in params.items() if k not in NON_INDICATOR_PARAMS}


def state_key(indicator: str, params: dict[str, Any] | None = None) -> str:
    """Key under which an indicator state is stored.

    Without params the bare indicator key is used (default parameters), so
    strategies written without params keep their historical behaviour.
    With params, each distinct parameter set gets its own state, e.g.
    ``ema|{"period": 200}``, so EMA 50 and EMA 200 can coexist.
    """
    clean = indicator_params(params)
    if not clean:
        return indicator
    return f"{indicator}|{json.dumps(clean, sort_keys=True)}"


def normalize_filters(filters: Any) -> dict[str, Any]:
    """Convert the list filter format into the dict format read by the engine.

    List format (frontend / seed templates)::

        [{"type": "ema_trend", "params": {"period": 50}, "enabled": true}]

    Dict format (SignalFilter.check_all)::

        {"ema_trend": {"enabled": true, "ema_period": 50}}
    """
    if not filters:
        return {}
    if isinstance(filters, dict):
        return filters
    normalized: dict[str, Any] = {}
    for item in filters:
        if not isinstance(item, dict) or not item.get("type"):
            continue
        ftype = item["type"]
        params = dict(item.get("params") or {})
        cfg: dict[str, Any] = {"enabled": item.get("enabled", True)}
        if ftype == "ema_trend":
            if "period" in params:
                cfg["ema_period"] = params.pop("period")
            params.pop("indicator", None)
            params.pop("operator", None)
        elif ftype == "adx_trend":
            if "period" in params:
                cfg["adx_period"] = params.pop("period")
            params.pop("indicator", None)
        cfg.update(params)
        normalized[ftype] = cfg
    return normalized


# filter type -> (indicator key, filter field holding its period)
TREND_FILTER_INDICATORS = {
    "ema_trend": ("ema", "ema_period"),
    "adx_trend": ("adx_dmi", "adx_period"),
}


def trend_filter_specs(filters: Any) -> dict[str, tuple[str, dict[str, Any] | None]]:
    """Indicator (key, params) read by each enabled trend filter.

    Params are None when the filter uses the indicator's default period.
    """
    normalized = normalize_filters(filters)
    specs: dict[str, tuple[str, dict[str, Any] | None]] = {}
    for ftype, (indicator, period_field) in TREND_FILTER_INDICATORS.items():
        cfg = normalized.get(ftype)
        if isinstance(cfg, dict) and cfg.get("enabled", True):
            params = {"period": cfg[period_field]} if period_field in cfg else None
            specs[ftype] = (indicator, params)
    return specs


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
        config.filters = normalize_filters(config.filters)

        # Auto-detect which indicators the strategy needs.
        if not config.indicators_needed:
            config.indicators_needed = self._extract_indicators(config)

        return config

    def indicator_specs(self, config: StrategyConfig) -> dict[str, tuple[str, dict[str, Any]]]:
        """List every indicator state the engine must compute.

        Returns:
            Mapping ``state_key -> (indicator_key, params)``. Includes the
            default-parameter state of every ``indicators_needed`` entry,
            one state per distinct params found in the conditions, and the
            states required by the ema_trend / adx_trend filters.
        """
        specs: dict[str, tuple[str, dict[str, Any]]] = {}

        def add(indicator: str, params: dict[str, Any] | None = None) -> None:
            clean = indicator_params(params)
            specs.setdefault(state_key(indicator, clean), (indicator, clean))

        for key in config.indicators_needed:
            add(key)

        def walk(node: Any) -> None:
            if isinstance(node, list):
                for child in node:
                    walk(child)
            elif isinstance(node, dict):
                if "indicator" in node:
                    add(node["indicator"], node.get("params"))
                for child in node.get("conditions", []):
                    walk(child)

        walk(config.entry_conditions)
        walk(config.exit_conditions)

        for indicator, params in trend_filter_specs(config.filters).values():
            add(indicator, params)

        return specs

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

        # Validate condition structure (list or tree format).
        for label, tree in [
            ("entry_conditions", config.entry_conditions),
            ("exit_conditions", config.exit_conditions),
        ]:
            if tree:
                if isinstance(tree, list):
                    for i, node in enumerate(tree):
                        tree_errors = self._validate_condition_tree(node, f"{label}[{i}]")
                        errors.extend(tree_errors)
                elif isinstance(tree, dict):
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
        """Walk the condition trees/lists and collect all indicator keys."""
        keys: set[str] = set()
        for tree in (config.entry_conditions, config.exit_conditions):
            if tree:
                # Handle both list format (from frontend) and tree format
                if isinstance(tree, list):
                    for item in tree:
                        self._collect_indicator_keys(item, keys)
                elif isinstance(tree, dict):
                    self._collect_indicator_keys(tree, keys)
        return sorted(keys)

    def _collect_indicator_keys(
        self, node: dict[str, Any], keys: set[str]
    ) -> None:
        """Recursively collect indicator keys from a condition node/tree."""
        if not isinstance(node, dict):
            return
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
