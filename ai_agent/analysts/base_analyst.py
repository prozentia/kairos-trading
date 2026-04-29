"""Base class for all AI analyst agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import MarketSnapshot, AgentSignal


class BaseAnalyst(ABC):
    """Abstract base analyst. Each analyst receives a MarketSnapshot
    and returns an AgentSignal with a score between 0.0 and 1.0."""

    name: str = "base"

    @abstractmethod
    async def analyze(self, snapshot: MarketSnapshot) -> AgentSignal:
        """Analyze market snapshot and produce a signal.

        Args:
            snapshot: Current market state.

        Returns:
            AgentSignal with score 0.0 (bearish) to 1.0 (bullish).
        """
        ...
