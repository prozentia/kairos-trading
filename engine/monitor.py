"""Position monitor — watches open positions for exit conditions.

Checks stop-loss, trailing stop, take-profit levels, and time-based exits.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from core.models import Candle, Position, PositionStatus

logger = logging.getLogger(__name__)


@dataclass
class ExitSignal:
    """Signal indicating a position should be closed."""

    pair: str
    reason: str  # "stop_loss" | "trailing_stop" | "take_profit" | "time_exit"
    exit_price: float
    position: Position


class PositionMonitor:
    """Monitors open positions and generates exit signals."""

    def __init__(
        self,
        trailing_activation_pct: float = 0.5,
        trailing_callback_pct: float = 0.3,
        max_hold_seconds: int = 3600,
    ) -> None:
        self._trailing_activation_pct = trailing_activation_pct
        self._trailing_callback_pct = trailing_callback_pct
        self._max_hold_seconds = max_hold_seconds

    def check_exits(
        self,
        positions: list[Position],
        candle: Candle,
    ) -> list[ExitSignal]:
        """Check all open positions for exit conditions.

        Args:
            positions: List of open positions.
            candle: Latest candle data.

        Returns:
            List of ExitSignal for positions that should be closed.
        """
        exits: list[ExitSignal] = []

        for pos in positions:
            if not pos.is_open or pos.pair != candle.pair:
                continue

            signal = self._check_position(pos, candle)
            if signal:
                exits.append(signal)

        return exits

    def _check_position(self, pos: Position, candle: Candle) -> ExitSignal | None:
        """Check a single position for exit conditions."""
        # Update PnL
        pos.update_pnl(candle.close)

        # 1. Stop-loss hit
        if pos.stop_loss > 0 and candle.low <= pos.stop_loss:
            return ExitSignal(
                pair=pos.pair,
                reason="stop_loss",
                exit_price=pos.stop_loss,
                position=pos,
            )

        # 2. Trailing stop
        trailing_exit = self._check_trailing(pos, candle)
        if trailing_exit:
            return trailing_exit

        # 3. Take-profit levels
        tp_exit = self._check_take_profit(pos, candle)
        if tp_exit:
            return tp_exit

        # 4. Time-based exit
        if self._max_hold_seconds > 0:
            elapsed = (candle.timestamp - pos.entry_time).total_seconds()
            if elapsed >= self._max_hold_seconds:
                return ExitSignal(
                    pair=pos.pair,
                    reason="time_exit",
                    exit_price=candle.close,
                    position=pos,
                )

        return None

    def _check_trailing(self, pos: Position, candle: Candle) -> ExitSignal | None:
        """Check and update trailing stop."""
        pnl_pct = pos.current_pnl_pct

        # Activate trailing if not already
        if not pos.trailing_active and pnl_pct >= self._trailing_activation_pct:
            pos.trailing_active = True
            pos.trailing_high = candle.high
            logger.debug("Trailing stop activated for %s at %.2f%%", pos.pair, pnl_pct)

        if not pos.trailing_active:
            return None

        # Update trailing high
        if candle.high > pos.trailing_high:
            pos.trailing_high = candle.high

        # Check callback
        if pos.trailing_high > 0:
            drop_from_high = ((pos.trailing_high - candle.close) / pos.trailing_high) * 100
            if drop_from_high >= self._trailing_callback_pct:
                return ExitSignal(
                    pair=pos.pair,
                    reason="trailing_stop",
                    exit_price=candle.close,
                    position=pos,
                )

        return None

    def _check_take_profit(self, pos: Position, candle: Candle) -> ExitSignal | None:
        """Check take-profit levels (partial or full)."""
        for tp in pos.take_profit_levels:
            tp_price = tp.get("price", 0.0)
            if tp_price > 0 and candle.high >= tp_price:
                return ExitSignal(
                    pair=pos.pair,
                    reason="take_profit",
                    exit_price=tp_price,
                    position=pos,
                )
        return None
