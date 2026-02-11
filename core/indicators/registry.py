"""Indicator registry with auto-discovery and decorator-based registration.

Usage in an indicator module::

    from core.indicators.registry import register
    from core.indicators.base import BaseIndicator

    @register
    class RSI(BaseIndicator):
        key = "rsi"
        ...

The registry is a module-level singleton so that importing it from
anywhere returns the same instance.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from core.indicators.base import BaseIndicator


class IndicatorRegistry:
    """Central catalogue of all available indicator implementations."""

    def __init__(self) -> None:
        self._indicators: dict[str, BaseIndicator] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_class(self, cls: type[BaseIndicator]) -> type[BaseIndicator]:
        """Register an indicator class (instantiates it).

        Can be used as a decorator::

            @registry.register_class
            class EMA(BaseIndicator): ...
        """
        instance = cls()
        if not instance.key:
            raise ValueError(f"{cls.__name__} must define a non-empty 'key' attribute.")
        if instance.key in self._indicators:
            raise ValueError(f"Duplicate indicator key: {instance.key!r}")
        self._indicators[instance.key] = instance
        return cls

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, key: str) -> BaseIndicator:
        """Return the indicator instance for *key*, or raise KeyError."""
        if key not in self._indicators:
            raise KeyError(f"Unknown indicator: {key!r}. Available: {list(self._indicators)}")
        return self._indicators[key]

    def all(self) -> dict[str, BaseIndicator]:
        """Return a copy of the full registry mapping."""
        return dict(self._indicators)

    def by_category(self, category: str) -> list[BaseIndicator]:
        """Return all indicators belonging to *category*."""
        return [ind for ind in self._indicators.values() if ind.category == category]

    def keys(self) -> list[str]:
        """Return sorted list of registered indicator keys."""
        return sorted(self._indicators)

    # ------------------------------------------------------------------
    # Auto-discovery
    # ------------------------------------------------------------------

    def discover(self, package_path: str = "core.indicators") -> None:
        """Import every module in the indicators package so that
        ``@register`` decorators execute and populate the registry.
        """
        pkg = importlib.import_module(package_path)
        for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
            if modname in ("base", "registry", "__init__"):
                continue
            importlib.import_module(f"{package_path}.{modname}")

    def __len__(self) -> int:
        return len(self._indicators)

    def __contains__(self, key: str) -> bool:
        return key in self._indicators

    def __repr__(self) -> str:
        return f"<IndicatorRegistry indicators={len(self._indicators)}>"


# ------------------------------------------------------------------
# Module-level singleton & convenience decorator
# ------------------------------------------------------------------

_registry = IndicatorRegistry()


def register(cls: type[BaseIndicator]) -> type[BaseIndicator]:
    """Module-level decorator that registers an indicator class.

    Example::

        @register
        class EMA(BaseIndicator):
            key = "ema"
            ...
    """
    return _registry.register_class(cls)


def get_registry() -> IndicatorRegistry:
    """Return the global registry singleton."""
    return _registry
