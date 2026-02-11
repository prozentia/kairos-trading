"""Position-level risk management.

Monitors an open position tick-by-tick and emits SELL / EMERGENCY_SELL
signals when stop-loss, trailing stop, take-profit, or time-based exit
conditions are met.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.models import Position, Signal, SignalType


class PositionManager:
    """Evaluate exit conditions for a single open position."""

    def update_position(
        self,
        position: Position,
        current_price: float,
        timestamp: datetime | None = None,
    ) -> list[Signal]:
        """Check all exit conditions and return any triggered signals.

        This is called on every price update for an open position.
        Multiple signals can be returned (e.g. both trailing stop and
        time-based), but normally only the first one is acted upon.

        Args:
            position: The open position to check.
            current_price: Latest market price.
            timestamp: Current time (defaults to utcnow).

        Returns:
            List of exit signals (empty if nothing triggers).
        """
        if not position.is_open:
            return []

        timestamp = timestamp or datetime.utcnow()
        position.update_pnl(current_price)

        signals: list[Signal] = []

        checks = [
            self._check_stop_loss,
            self._check_trailing_stop,
            self._check_take_profit,
            self._check_time_based_exit,
        ]

        for check_fn in checks:
            signal = check_fn(position, current_price, timestamp)
            if signal is not None:
                signals.append(signal)

        return signals

    # ------------------------------------------------------------------
    # Exit checks
    # ------------------------------------------------------------------

    def _check_stop_loss(
        self,
        position: Position,
        price: float,
        timestamp: datetime,
    ) -> Signal | None:
        """Emit SELL if price dropped below the fixed stop-loss level.

        The stop-loss level is stored in ``position.stop_loss``.
        """
        raise NotImplementedError

    def _check_trailing_stop(
        self,
        position: Position,
        price: float,
        timestamp: datetime,
    ) -> Signal | None:
        """Manage trailing stop: activate when profit threshold is met,
        then follow price upward.  Emit SELL if price drops below the
        trailing level.

        Reads/writes:
            position.trailing_active
            position.trailing_high
            position.metadata["trailing_activation_pct"]
            position.metadata["trailing_distance_pct"]
        """
        raise NotImplementedError

    def _check_take_profit(
        self,
        position: Position,
        price: float,
        timestamp: datetime,
    ) -> Signal | None:
        """Check take-profit levels (supports partial exits).

        Reads:
            position.take_profit_levels: list of
                {"price": float, "pct_to_close": float, "hit": bool}
        """
        raise NotImplementedError

    def _check_time_based_exit(
        self,
        position: Position,
        price: float,
        timestamp: datetime,
    ) -> Signal | None:
        """Close position if it has been open longer than max duration.

        Reads:
            position.metadata["max_hold_minutes"] (int | None)
        """
        raise NotImplementedError
