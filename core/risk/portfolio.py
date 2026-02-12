"""Portfolio-level risk management.

Enforces global limits across all open positions: max concurrent
positions, total exposure, daily loss cap, and drawdown protection.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.models import Position, RiskLimits, Trade


class PortfolioManager:
    """Track portfolio state and enforce risk limits."""

    def __init__(self, risk_limits: RiskLimits) -> None:
        self.risk_limits = risk_limits

    # ------------------------------------------------------------------
    # Position gating
    # ------------------------------------------------------------------

    def can_open_position(
        self,
        open_positions: list[Position],
        balance: float,
        daily_trade_count: int = 0,
        daily_pnl_pct: float = 0.0,
    ) -> tuple[bool, str]:
        """Check whether opening a new position is allowed.

        Checks:
            - max_positions not exceeded.
            - max_daily_trades not exceeded.
            - daily loss limit not breached.

        Args:
            open_positions: Currently open positions.
            balance: Total available capital (quote currency).
            daily_trade_count: Number of trades executed today.
            daily_pnl_pct: Cumulative daily PnL as percentage.

        Returns:
            (True, "") if allowed, (False, reason) otherwise.
        """
        # Check max positions.
        if len(open_positions) >= self.risk_limits.max_positions:
            return False, (
                f"Max positions reached: {len(open_positions)}"
                f"/{self.risk_limits.max_positions}."
            )

        # Check max daily trades.
        if daily_trade_count >= self.risk_limits.max_daily_trades:
            return False, (
                f"Max daily trades reached: {daily_trade_count}"
                f"/{self.risk_limits.max_daily_trades}."
            )

        # Check daily loss limit.
        if daily_pnl_pct < 0 and abs(daily_pnl_pct) >= self.risk_limits.max_daily_loss_pct:
            return False, (
                f"Daily loss limit breached: {daily_pnl_pct:.2f}% "
                f"(limit: -{self.risk_limits.max_daily_loss_pct:.2f}%)."
            )

        # Check available capital.
        if balance <= 0.0:
            return False, "No available capital."

        return True, ""

    # ------------------------------------------------------------------
    # Circuit breakers
    # ------------------------------------------------------------------

    def check_circuit_breakers(
        self,
        trades_today: list[Trade],
        daily_pnl_pct: float,
        capital: float = 0.0,
    ) -> tuple[bool, str]:
        """Check circuit breaker conditions.

        Breakers:
            - 3 consecutive losses -> pause 30 min.
            - 10% daily loss -> pause 24h.
            - Capital exhausted -> force CRAWL mode.

        Args:
            trades_today: List of today's completed trades.
            daily_pnl_pct: Cumulative daily PnL as percentage.
            capital: Current available capital.

        Returns:
            (True, "") if trading can continue,
            (False, reason) if a breaker tripped.
        """
        # Check consecutive losses.
        consecutive_losses = self._count_consecutive_losses(trades_today)
        if consecutive_losses >= 3:
            return False, (
                f"Circuit breaker: {consecutive_losses} consecutive losses. "
                f"Pause 30 min."
            )

        # Check 10% daily loss.
        if daily_pnl_pct < 0 and abs(daily_pnl_pct) >= 10.0:
            return False, (
                f"Circuit breaker: daily loss {daily_pnl_pct:.2f}% "
                f"exceeds -10%. Pause 24h."
            )

        # Check capital exhaustion.
        if capital <= 0.0 and len(trades_today) > 0:
            return False, "Circuit breaker: capital exhausted. Force CRAWL mode."

        return True, ""

    # ------------------------------------------------------------------
    # Daily statistics
    # ------------------------------------------------------------------

    def calculate_daily_stats(self, trades: list[Trade]) -> dict[str, Any]:
        """Calculate daily trading statistics from a list of trades.

        Args:
            trades: List of completed trades for the day.

        Returns:
            Dict with keys: total_trades, wins, losses, win_rate,
            total_pnl, avg_pnl, max_win, max_loss, sharpe (simplified),
            max_drawdown, profit_factor.
        """
        if not trades:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
            }

        pnls = [t.pnl_usdt for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_pnl = sum(pnls)
        avg_pnl = total_pnl / len(pnls) if pnls else 0.0
        win_rate = (len(wins) / len(pnls) * 100.0) if pnls else 0.0

        # Simplified Sharpe: mean / std of returns.
        sharpe = 0.0
        if len(pnls) > 1:
            mean = avg_pnl
            variance = sum((p - mean) ** 2 for p in pnls) / (len(pnls) - 1)
            std = variance ** 0.5
            if std > 0:
                sharpe = mean / std

        # Max drawdown from cumulative PnL.
        max_drawdown = self._calculate_max_drawdown(pnls)

        # Profit factor: sum(wins) / abs(sum(losses)).
        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else (
            float("inf") if total_wins > 0 else 0.0
        )

        return {
            "total_trades": len(pnls),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "max_win": max(wins) if wins else 0.0,
            "max_loss": min(losses) if losses else 0.0,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
        }

    # ------------------------------------------------------------------
    # Exposure
    # ------------------------------------------------------------------

    def get_exposure(
        self,
        positions: list[Position],
        current_prices: dict[str, float],
    ) -> dict[str, Any]:
        """Calculate current portfolio exposure.

        Args:
            positions: Open positions.
            current_prices: Mapping of pair -> current price.

        Returns:
            Dict with keys: total_exposure, per_pair (dict),
            exposure_pct (requires capital in context).
        """
        per_pair: dict[str, float] = {}
        total_exposure = 0.0

        for pos in positions:
            if not pos.is_open:
                continue
            price = current_prices.get(pos.pair, pos.entry_price)
            notional = pos.quantity * price
            per_pair[pos.pair] = per_pair.get(pos.pair, 0.0) + notional
            total_exposure += notional

        return {
            "total_exposure": total_exposure,
            "per_pair": per_pair,
            "position_count": len([p for p in positions if p.is_open]),
        }

    # ------------------------------------------------------------------
    # Correlation check
    # ------------------------------------------------------------------

    def check_correlation(
        self,
        positions: list[Position],
        correlation_matrix: dict[tuple[str, str], float] | None = None,
        threshold: float = 0.8,
    ) -> tuple[bool, str]:
        """Warn if too many correlated positions are open.

        Args:
            positions: Open positions.
            correlation_matrix: Pair correlations, e.g.
                {("BTC/USDT", "ETH/USDT"): 0.85}.
            threshold: Correlation threshold to flag (default 0.8).

        Returns:
            (True, "") if acceptable, (False, warning) if correlated.
        """
        if correlation_matrix is None or len(positions) < 2:
            return True, ""

        open_pairs = list({p.pair for p in positions if p.is_open})

        for i, pair_a in enumerate(open_pairs):
            for pair_b in open_pairs[i + 1:]:
                key1 = (pair_a, pair_b)
                key2 = (pair_b, pair_a)
                corr = correlation_matrix.get(key1) or correlation_matrix.get(key2)
                if corr is not None and abs(corr) >= threshold:
                    return False, (
                        f"High correlation ({corr:.2f}) between "
                        f"{pair_a} and {pair_b} (threshold: {threshold})."
                    )

        return True, ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_consecutive_losses(trades: list[Trade]) -> int:
        """Count consecutive losses from the most recent trade backward."""
        count = 0
        for trade in reversed(trades):
            if trade.pnl_usdt < 0:
                count += 1
            else:
                break
        return count

    @staticmethod
    def _calculate_max_drawdown(pnls: list[float]) -> float:
        """Calculate maximum drawdown from a series of PnL values.

        Returns drawdown as a positive number (e.g. 5.0 means $5 drawdown).
        """
        if not pnls:
            return 0.0

        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0

        for pnl in pnls:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        return max_dd
