"""Position sizing algorithms.

Standalone functions that compute how much capital to allocate to a
single trade.  All functions are pure and stateless.
"""

from __future__ import annotations

import math


class PositionSizer:
    """Collection of position-sizing strategies."""

    @staticmethod
    def fixed_percentage(capital: float, pct: float) -> float:
        """Allocate a fixed percentage of capital.

        Args:
            capital: Total available capital (quote currency).
            pct: Percentage to allocate (e.g. 10.0 for 10%).

        Returns:
            Position size in quote currency.
        """
        raise NotImplementedError

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        risk_reward: float,
        capital: float,
        fraction: float = 0.5,
    ) -> float:
        """Kelly Criterion position sizing.

        Calculates the theoretically optimal bet size.  *fraction* is
        a safety multiplier (half-Kelly by default) to reduce variance.

        Args:
            win_rate: Historical win rate (0.0 - 1.0).
            risk_reward: Average win / average loss ratio.
            capital: Total available capital.
            fraction: Kelly fraction multiplier (0.5 = half-Kelly).

        Returns:
            Position size in quote currency.
        """
        raise NotImplementedError

    @staticmethod
    def atr_based(
        capital: float,
        atr: float,
        risk_pct: float,
        price: float = 1.0,
    ) -> float:
        """ATR-based position sizing.

        Sizes the position so that a 1-ATR adverse move equals
        *risk_pct* of capital.  Larger ATR = smaller position.

        Args:
            capital: Total available capital.
            atr: Current ATR value.
            risk_pct: Maximum risk per trade as percentage (e.g. 1.0).
            price: Current asset price (for converting to quantity).

        Returns:
            Position size in quote currency.
        """
        raise NotImplementedError
