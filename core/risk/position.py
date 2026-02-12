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
        A value of 0.0 means no stop-loss is configured.
        """
        if position.stop_loss <= 0.0:
            return None

        # For a long position, SL triggers when price falls below.
        if position.side == "BUY" and price <= position.stop_loss:
            return self._make_exit_signal(
                position, price, timestamp,
                signal_type=SignalType.SELL,
                reason=f"STOP_LOSS hit at {price:.2f} (SL={position.stop_loss:.2f})",
            )

        # For a short position, SL triggers when price rises above.
        if position.side == "SELL" and price >= position.stop_loss:
            return self._make_exit_signal(
                position, price, timestamp,
                signal_type=SignalType.SELL,
                reason=f"STOP_LOSS hit at {price:.2f} (SL={position.stop_loss:.2f})",
            )

        return None

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
        activation_pct = position.metadata.get("trailing_activation_pct", 0.0)
        distance_pct = position.metadata.get("trailing_distance_pct", 0.0)

        # No trailing stop configured.
        if activation_pct <= 0.0 or distance_pct <= 0.0:
            return None

        # Calculate current profit percentage (long-only for now).
        if position.entry_price <= 0.0:
            return None

        if position.side == "BUY":
            profit_pct = ((price - position.entry_price) / position.entry_price) * 100.0
        else:
            profit_pct = ((position.entry_price - price) / position.entry_price) * 100.0

        # Activation: once profit exceeds the activation threshold.
        if not position.trailing_active:
            if profit_pct >= activation_pct:
                position.trailing_active = True
                position.trailing_high = price if position.side == "BUY" else price
            return None

        # Already active: update the trailing high.
        if position.side == "BUY":
            if price > position.trailing_high:
                position.trailing_high = price

            # Check if price dropped below trailing stop level.
            trailing_stop_price = position.trailing_high * (1.0 - distance_pct / 100.0)
            if price <= trailing_stop_price:
                return self._make_exit_signal(
                    position, price, timestamp,
                    signal_type=SignalType.SELL,
                    reason=(
                        f"TRAILING_STOP hit at {price:.2f} "
                        f"(high={position.trailing_high:.2f}, "
                        f"trail_sl={trailing_stop_price:.2f})"
                    ),
                )
        else:
            # Short position: trailing follows price downward.
            if price < position.trailing_high:
                position.trailing_high = price

            trailing_stop_price = position.trailing_high * (1.0 + distance_pct / 100.0)
            if price >= trailing_stop_price:
                return self._make_exit_signal(
                    position, price, timestamp,
                    signal_type=SignalType.SELL,
                    reason=(
                        f"TRAILING_STOP hit at {price:.2f} "
                        f"(low={position.trailing_high:.2f}, "
                        f"trail_sl={trailing_stop_price:.2f})"
                    ),
                )

        return None

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
        if not position.take_profit_levels:
            return None

        for level in position.take_profit_levels:
            tp_price = level.get("price", 0.0)
            already_hit = level.get("hit", False)

            if already_hit or tp_price <= 0.0:
                continue

            # Long: price reaches or exceeds TP.
            if position.side == "BUY" and price >= tp_price:
                level["hit"] = True
                pct_to_close = level.get("pct_to_close", 100.0)
                return self._make_exit_signal(
                    position, price, timestamp,
                    signal_type=SignalType.SELL,
                    reason=(
                        f"TAKE_PROFIT level {tp_price:.2f} hit "
                        f"(close {pct_to_close:.0f}%)"
                    ),
                    metadata={"pct_to_close": pct_to_close, "tp_price": tp_price},
                )

            # Short: price drops to or below TP.
            if position.side == "SELL" and price <= tp_price:
                level["hit"] = True
                pct_to_close = level.get("pct_to_close", 100.0)
                return self._make_exit_signal(
                    position, price, timestamp,
                    signal_type=SignalType.SELL,
                    reason=(
                        f"TAKE_PROFIT level {tp_price:.2f} hit "
                        f"(close {pct_to_close:.0f}%)"
                    ),
                    metadata={"pct_to_close": pct_to_close, "tp_price": tp_price},
                )

        return None

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
        max_hold = position.metadata.get("max_hold_minutes")
        if max_hold is None or max_hold <= 0:
            return None

        elapsed = timestamp - position.entry_time
        if elapsed >= timedelta(minutes=max_hold):
            return self._make_exit_signal(
                position, price, timestamp,
                signal_type=SignalType.SELL,
                reason=(
                    f"TIME_EXIT after {elapsed.total_seconds() / 60:.0f} min "
                    f"(max={max_hold} min)"
                ),
            )

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_exit_signal(
        position: Position,
        price: float,
        timestamp: datetime,
        signal_type: SignalType = SignalType.SELL,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Signal:
        """Build an exit signal for the given position."""
        return Signal(
            type=signal_type,
            pair=position.pair,
            timeframe="",
            price=price,
            timestamp=timestamp,
            strategy_name="",
            reason=reason,
            metadata=metadata or {},
        )
