"""Abstract base class for all technical indicators.

Every indicator must inherit from BaseIndicator and implement:
  - calculate()  : full computation over a candle history
  - update()     : incremental computation for one new candle
  - evaluate()   : check whether a named condition is satisfied
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.models import Candle


class BaseIndicator(ABC):
    """Contract that every indicator plugin must fulfil."""

    # Subclasses must set these class-level attributes.
    name: str = ""
    key: str = ""           # unique slug, e.g. "ema", "rsi", "bollinger"
    category: str = ""      # "trend" | "momentum" | "volatility" | "volume" | "special"
    default_params: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    @abstractmethod
    def calculate(self, candles: list[Candle], **params: Any) -> dict[str, Any]:
        """Compute the indicator over a full candle history.

        Args:
            candles: Ordered list of candles (oldest first).
            **params: Override default_params for this run.

        Returns:
            A dict keyed by output name (e.g. {"ema": [...], "signal": [...]}).
        """
        ...

    @abstractmethod
    def update(self, candle: Candle, state: dict[str, Any], **params: Any) -> dict[str, Any]:
        """Incrementally update the indicator state with one new candle.

        This is the hot-path called on every new candle so it must be
        efficient.  It receives the *previous* state dict returned by
        either calculate() or a prior update() call.

        Args:
            candle: The latest closed candle.
            state: Previous indicator state dict.
            **params: Override default_params.

        Returns:
            Updated state dict (may be mutated in-place).
        """
        ...

    @abstractmethod
    def evaluate(self, state: dict[str, Any], operator: str, value: Any = None) -> bool:
        """Evaluate a condition against the current indicator state.

        This is used by the strategy evaluator to check declarative
        conditions such as ``{"indicator": "rsi", "operator": "below", "value": 30}``.

        Args:
            state: Current indicator state dict.
            operator: Condition name, e.g. "above", "below", "cross_up".
            value: Optional threshold or reference value.

        Returns:
            True if the condition is met, False otherwise.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def merge_params(self, overrides: dict[str, Any]) -> dict[str, Any]:
        """Return default_params updated with any caller overrides."""
        merged = dict(self.default_params)
        merged.update(overrides)
        return merged

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} key={self.key!r} category={self.category!r}>"
