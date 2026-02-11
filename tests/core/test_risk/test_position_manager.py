"""Tests for position management (stop-loss, trailing stop, take-profit).

The position manager monitors open positions and generates exit signals
when risk thresholds are breached. Tests are skipped until the risk
module is implemented.
"""

from datetime import datetime, timezone

import pytest

from core.models import Position, PositionStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_position(
    entry_price: float = 97_500.0,
    stop_loss: float = 96_037.50,
    quantity: float = 0.001,
) -> Position:
    """Create a standard open long position."""
    return Position(
        pair="BTC/USDT",
        side="BUY",
        entry_price=entry_price,
        quantity=quantity,
        entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        stop_loss=stop_loss,
        trailing_active=False,
        trailing_high=0.0,
        entry_reason="TEST",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Position manager not implemented yet")
def test_stop_loss_triggered():
    """Stop-loss should trigger when price drops below stop_loss level."""
    pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
    current_price = 95_900.0  # Below stop-loss

    # exit_signal = position_manager.check_exit(pos, current_price)
    # assert exit_signal is not None
    # assert exit_signal.type == SignalType.SELL
    # assert "STOP_LOSS" in exit_signal.reason


@pytest.mark.skip(reason="Position manager not implemented yet")
def test_trailing_stop_activation():
    """Trailing stop should activate when PnL exceeds activation threshold."""
    pos = _open_position(entry_price=97_500.0)
    # Price up 0.6% -> should activate trailing
    activation_price = 97_500.0 * 1.006  # 98085.0

    # risk_config = {"trailing_activation_pct": 0.6, "trailing_distance_pct": 0.3}
    # position_manager.update_trailing(pos, activation_price, risk_config)
    # assert pos.trailing_active is True
    # assert pos.trailing_high == pytest.approx(activation_price)


@pytest.mark.skip(reason="Position manager not implemented yet")
def test_trailing_stop_triggered():
    """Trailing stop should trigger when price drops from trailing high."""
    pos = _open_position(entry_price=97_500.0)
    pos.trailing_active = True
    pos.trailing_high = 98_200.0

    # Price drops 0.3% from trailing high
    trigger_price = 98_200.0 * (1 - 0.003)  # ~97905.4
    current_price = 97_850.0  # Below trigger

    # risk_config = {"trailing_distance_pct": 0.3}
    # exit_signal = position_manager.check_exit(pos, current_price, risk_config)
    # assert exit_signal is not None
    # assert "TRAILING_STOP" in exit_signal.reason


@pytest.mark.skip(reason="Position manager not implemented yet")
def test_take_profit_triggered():
    """Take-profit should trigger at defined levels."""
    pos = _open_position(entry_price=97_500.0)
    # TP at +1%
    current_price = 97_500.0 * 1.01  # 98475.0

    # risk_config = {
    #     "take_profit_levels": [{"pct": 1.0, "close_pct": 50.0}],
    # }
    # exit_signal = position_manager.check_exit(pos, current_price, risk_config)
    # assert exit_signal is not None
    # assert "TAKE_PROFIT" in exit_signal.reason


@pytest.mark.skip(reason="Position manager not implemented yet")
def test_no_exit_signal():
    """No exit signal when price is within normal range."""
    pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
    current_price = 97_600.0  # Slightly above entry, no trailing yet

    # risk_config = {
    #     "trailing_activation_pct": 0.6,
    #     "trailing_distance_pct": 0.3,
    #     "take_profit_levels": [{"pct": 1.0, "close_pct": 50.0}],
    # }
    # exit_signal = position_manager.check_exit(pos, current_price, risk_config)
    # assert exit_signal is None  # No exit needed
