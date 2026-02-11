"""Post-signal filters applied after the strategy evaluator produces a BUY.

These are portfolio-level and timing-level checks that can reject an
otherwise valid signal.  Each filter returns (passed: bool, reason: str).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.models import StrategyConfig


class PostSignalFilters:
    """Collection of filters that gate entry signals."""

    def check_all(
        self,
        strategy_config: StrategyConfig,
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Run every enabled filter.  Returns (True, "") if all pass.

        Args:
            strategy_config: Strategy definition (filters section).
            context: Runtime context with current state data.

        Returns:
            (True, "") on success, (False, reason) on first failure.
        """
        filters = strategy_config.filters
        if not filters:
            return True, ""

        checks = [
            ("ema_trend", self._check_ema_trend),
            ("trading_hours", self._check_trading_hours),
            ("loss_cooldown", self._check_loss_cooldown),
            ("max_daily_trades", self._check_max_daily_trades),
            ("max_daily_loss", self._check_max_daily_loss),
        ]

        for filter_key, check_fn in checks:
            if filter_key in filters and filters[filter_key].get("enabled", False):
                passed, reason = check_fn(filters[filter_key], context)
                if not passed:
                    return False, reason

        return True, ""

    # ------------------------------------------------------------------
    # Individual filters
    # ------------------------------------------------------------------

    def _check_ema_trend(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if price is below a macro EMA (e.g. EMA 50 on 1h).

        Config keys:
            period (int): EMA period, default 50.
            timeframe (str): Timeframe for the EMA, default "1h".

        Context keys:
            ema_trend_value (float): Pre-computed EMA value.
            price (float): Current price.
        """
        raise NotImplementedError

    def _check_trading_hours(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY outside configured trading hours.

        Config keys:
            start_hour (int): UTC hour to start trading.
            end_hour (int): UTC hour to stop trading.

        Context keys:
            timestamp (datetime): Current UTC timestamp.
        """
        raise NotImplementedError

    def _check_loss_cooldown(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if a loss occurred within the cooldown window.

        Config keys:
            cooldown_minutes (int): Minutes to wait after a losing trade.

        Context keys:
            last_loss_time (datetime | None): Timestamp of last losing trade.
            timestamp (datetime): Current UTC timestamp.
        """
        raise NotImplementedError

    def _check_max_daily_trades(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if the daily trade count limit is reached.

        Config keys:
            max_trades (int): Maximum trades per day.

        Context keys:
            daily_trade_count (int): Trades executed today.
        """
        raise NotImplementedError

    def _check_max_daily_loss(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str]:
        """Reject BUY if daily cumulative loss exceeds threshold.

        Config keys:
            max_loss_pct (float): Maximum daily loss as percentage of capital.

        Context keys:
            daily_pnl_pct (float): Cumulative daily PnL as percentage.
        """
        raise NotImplementedError
