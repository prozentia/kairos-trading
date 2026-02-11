"""Portfolio-level risk management.

Enforces global limits across all open positions: max concurrent
positions, total exposure, daily loss cap, and drawdown protection.
"""

from __future__ import annotations

from typing import Any

from core.models import Position, RiskLimits


class PortfolioRiskManager:
    """Gate-keeper that decides whether a new position can be opened."""

    def can_open_position(
        self,
        positions: list[Position],
        risk_limits: RiskLimits,
        new_position_size: float,
        capital: float = 0.0,
    ) -> tuple[bool, str]:
        """Check whether opening a new position is allowed.

        Args:
            positions: Currently open positions.
            risk_limits: Portfolio risk constraints.
            new_position_size: Notional value of the proposed position.
            capital: Total available capital (quote currency).

        Returns:
            (True, "") if allowed, (False, reason) otherwise.
        """
        raise NotImplementedError

    def calculate_position_size(
        self,
        capital: float,
        risk_limits: RiskLimits,
        atr_value: float | None = None,
    ) -> float:
        """Determine the position size in quote currency.

        Uses ``risk_limits.position_size_pct`` as the base fraction of
        capital.  If *atr_value* is provided, the size can be adjusted
        for volatility.

        Args:
            capital: Available capital.
            risk_limits: Risk parameters.
            atr_value: Optional ATR for volatility-adjusted sizing.

        Returns:
            Position size in quote currency.
        """
        raise NotImplementedError

    def get_risk_metrics(
        self,
        positions: list[Position],
        capital: float,
    ) -> dict[str, Any]:
        """Compute a snapshot of portfolio risk metrics.

        Returns a dict with keys such as:
            open_positions (int)
            total_exposure (float)
            exposure_pct (float)
            unrealised_pnl (float)
            max_single_loss (float)
        """
        raise NotImplementedError
