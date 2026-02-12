"""Tests for position management (stop-loss, trailing stop, take-profit, time exit).

The PositionManager monitors open positions and generates exit signals
when risk thresholds are breached.
"""

from datetime import datetime, timedelta, timezone

import pytest

from core.models import Position, PositionStatus, Signal, SignalType
from core.risk.position import PositionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_position(
    entry_price: float = 97_500.0,
    stop_loss: float = 96_037.50,
    quantity: float = 0.001,
    side: str = "BUY",
    entry_time: datetime | None = None,
    metadata: dict | None = None,
    take_profit_levels: list | None = None,
) -> Position:
    """Create a standard open position."""
    return Position(
        pair="BTC/USDT",
        side=side,
        entry_price=entry_price,
        quantity=quantity,
        entry_time=entry_time or datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        stop_loss=stop_loss,
        trailing_active=False,
        trailing_high=0.0,
        take_profit_levels=take_profit_levels or [],
        current_pnl_pct=0.0,
        status=PositionStatus.OPEN,
        entry_reason="TEST",
        metadata=metadata or {},
    )


TS = datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Stop-loss tests
# ---------------------------------------------------------------------------

class TestStopLoss:
    """Test stop-loss exit logic."""

    def test_stop_loss_triggered_long(self):
        """SL triggers when price falls below stop_loss for a long."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
        signals = pm.update_position(pos, current_price=95_900.0, timestamp=TS)

        assert len(signals) >= 1
        sl_signals = [s for s in signals if "STOP_LOSS" in s.reason]
        assert len(sl_signals) == 1
        assert sl_signals[0].type == SignalType.SELL

    def test_stop_loss_not_triggered(self):
        """No SL when price is above stop_loss."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
        signals = pm.update_position(pos, current_price=97_600.0, timestamp=TS)

        sl_signals = [s for s in signals if "STOP_LOSS" in s.reason]
        assert len(sl_signals) == 0

    def test_stop_loss_at_exact_level(self):
        """SL triggers when price equals stop_loss exactly."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
        signals = pm.update_position(pos, current_price=96_037.50, timestamp=TS)

        sl_signals = [s for s in signals if "STOP_LOSS" in s.reason]
        assert len(sl_signals) == 1

    def test_stop_loss_disabled(self):
        """No SL check when stop_loss is 0."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=0.0)
        signals = pm.update_position(pos, current_price=50_000.0, timestamp=TS)

        sl_signals = [s for s in signals if "STOP_LOSS" in s.reason]
        assert len(sl_signals) == 0

    def test_stop_loss_short_position(self):
        """SL triggers when price rises above stop_loss for a short."""
        pm = PositionManager()
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=99_000.0,
            side="SELL",
        )
        signals = pm.update_position(pos, current_price=99_100.0, timestamp=TS)

        sl_signals = [s for s in signals if "STOP_LOSS" in s.reason]
        assert len(sl_signals) == 1


# ---------------------------------------------------------------------------
# Trailing stop tests
# ---------------------------------------------------------------------------

class TestTrailingStop:
    """Test trailing stop activation and trigger."""

    def _trailing_position(self, **kwargs) -> Position:
        """Create a position with trailing stop metadata."""
        meta = {
            "trailing_activation_pct": 0.6,
            "trailing_distance_pct": 0.3,
        }
        meta.update(kwargs.pop("extra_meta", {}))
        return _open_position(metadata=meta, **kwargs)

    def test_trailing_not_activated_below_threshold(self):
        """Trailing does not activate when profit is below threshold."""
        pm = PositionManager()
        pos = self._trailing_position(entry_price=97_500.0, stop_loss=96_037.50)

        # Price up 0.3% -> below 0.6% activation.
        price = 97_500.0 * 1.003
        pm.update_position(pos, current_price=price, timestamp=TS)

        assert pos.trailing_active is False

    def test_trailing_activates_above_threshold(self):
        """Trailing activates when profit exceeds activation_pct."""
        pm = PositionManager()
        pos = self._trailing_position(entry_price=97_500.0, stop_loss=96_037.50)

        # Price up 0.7% -> above 0.6% activation.
        price = 97_500.0 * 1.007
        pm.update_position(pos, current_price=price, timestamp=TS)

        assert pos.trailing_active is True
        assert pos.trailing_high == pytest.approx(price)

    def test_trailing_high_updates_upward(self):
        """Trailing high follows price upward."""
        pm = PositionManager()
        pos = self._trailing_position(entry_price=97_500.0, stop_loss=96_037.50)

        # Activate trailing.
        price1 = 97_500.0 * 1.007
        pm.update_position(pos, current_price=price1, timestamp=TS)
        assert pos.trailing_active is True

        # Price goes higher.
        price2 = 97_500.0 * 1.01
        pm.update_position(pos, current_price=price2, timestamp=TS)
        assert pos.trailing_high == pytest.approx(price2)

    def test_trailing_stop_triggered(self):
        """Trailing stop triggers when price drops from high by distance_pct."""
        pm = PositionManager()
        pos = self._trailing_position(entry_price=97_500.0, stop_loss=96_037.50)

        # Activate and set a high.
        pos.trailing_active = True
        pos.trailing_high = 98_200.0

        # Price drops 0.3% from trailing high -> should trigger.
        trigger_price = 98_200.0 * (1.0 - 0.003)
        current_price = trigger_price - 10.0  # Below the trigger.

        signals = pm.update_position(pos, current_price=current_price, timestamp=TS)
        trailing_signals = [s for s in signals if "TRAILING_STOP" in s.reason]
        assert len(trailing_signals) == 1
        assert trailing_signals[0].type == SignalType.SELL

    def test_trailing_stop_not_triggered_within_distance(self):
        """No trailing trigger if price drop is within distance."""
        pm = PositionManager()
        pos = self._trailing_position(entry_price=97_500.0, stop_loss=96_037.50)

        pos.trailing_active = True
        pos.trailing_high = 98_200.0

        # Price drops only 0.1% from trailing high -> should NOT trigger.
        price = 98_200.0 * 0.999
        signals = pm.update_position(pos, current_price=price, timestamp=TS)
        trailing_signals = [s for s in signals if "TRAILING_STOP" in s.reason]
        assert len(trailing_signals) == 0

    def test_trailing_no_config(self):
        """No trailing when metadata is empty."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)

        price = 97_500.0 * 1.01
        signals = pm.update_position(pos, current_price=price, timestamp=TS)
        trailing_signals = [s for s in signals if "TRAILING_STOP" in s.reason]
        assert len(trailing_signals) == 0
        assert pos.trailing_active is False


# ---------------------------------------------------------------------------
# Take-profit tests
# ---------------------------------------------------------------------------

class TestTakeProfit:
    """Test take-profit exit logic."""

    def test_take_profit_triggered(self):
        """TP triggers when price reaches TP level."""
        pm = PositionManager()
        tp_levels = [{"price": 98_475.0, "pct_to_close": 50.0, "hit": False}]
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            take_profit_levels=tp_levels,
        )

        signals = pm.update_position(pos, current_price=98_500.0, timestamp=TS)
        tp_signals = [s for s in signals if "TAKE_PROFIT" in s.reason]
        assert len(tp_signals) == 1
        assert tp_levels[0]["hit"] is True

    def test_take_profit_not_triggered_below(self):
        """TP does not trigger when price is below TP level."""
        pm = PositionManager()
        tp_levels = [{"price": 98_475.0, "pct_to_close": 50.0, "hit": False}]
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            take_profit_levels=tp_levels,
        )

        signals = pm.update_position(pos, current_price=98_000.0, timestamp=TS)
        tp_signals = [s for s in signals if "TAKE_PROFIT" in s.reason]
        assert len(tp_signals) == 0
        assert tp_levels[0]["hit"] is False

    def test_take_profit_already_hit(self):
        """TP does not trigger again if already hit."""
        pm = PositionManager()
        tp_levels = [{"price": 98_475.0, "pct_to_close": 50.0, "hit": True}]
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            take_profit_levels=tp_levels,
        )

        signals = pm.update_position(pos, current_price=99_000.0, timestamp=TS)
        tp_signals = [s for s in signals if "TAKE_PROFIT" in s.reason]
        assert len(tp_signals) == 0

    def test_multiple_take_profit_levels(self):
        """Only the first unhit TP level triggers."""
        pm = PositionManager()
        tp_levels = [
            {"price": 98_000.0, "pct_to_close": 30.0, "hit": True},
            {"price": 99_000.0, "pct_to_close": 50.0, "hit": False},
            {"price": 100_000.0, "pct_to_close": 20.0, "hit": False},
        ]
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            take_profit_levels=tp_levels,
        )

        signals = pm.update_position(pos, current_price=99_500.0, timestamp=TS)
        tp_signals = [s for s in signals if "TAKE_PROFIT" in s.reason]
        # Should trigger level 2 (99_000) but not level 3 (100_000).
        assert len(tp_signals) == 1
        assert tp_levels[1]["hit"] is True
        assert tp_levels[2]["hit"] is False

    def test_no_take_profit_levels(self):
        """No TP check when take_profit_levels is empty."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
        signals = pm.update_position(pos, current_price=200_000.0, timestamp=TS)
        tp_signals = [s for s in signals if "TAKE_PROFIT" in s.reason]
        assert len(tp_signals) == 0


# ---------------------------------------------------------------------------
# Time-based exit tests
# ---------------------------------------------------------------------------

class TestTimeBasedExit:
    """Test time-based exit logic."""

    def test_time_exit_triggered(self):
        """Time exit triggers after max_hold_minutes."""
        pm = PositionManager()
        entry = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            entry_time=entry,
            metadata={"max_hold_minutes": 60},
        )

        # 90 minutes later -> should trigger.
        ts = entry + timedelta(minutes=90)
        signals = pm.update_position(pos, current_price=97_600.0, timestamp=ts)
        time_signals = [s for s in signals if "TIME_EXIT" in s.reason]
        assert len(time_signals) == 1

    def test_time_exit_not_triggered(self):
        """Time exit does not trigger before max_hold_minutes."""
        pm = PositionManager()
        entry = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            entry_time=entry,
            metadata={"max_hold_minutes": 60},
        )

        # 30 minutes later -> should NOT trigger.
        ts = entry + timedelta(minutes=30)
        signals = pm.update_position(pos, current_price=97_600.0, timestamp=ts)
        time_signals = [s for s in signals if "TIME_EXIT" in s.reason]
        assert len(time_signals) == 0

    def test_time_exit_no_config(self):
        """No time exit when max_hold_minutes is not set."""
        pm = PositionManager()
        entry = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50, entry_time=entry)

        ts = entry + timedelta(hours=24)
        signals = pm.update_position(pos, current_price=97_600.0, timestamp=ts)
        time_signals = [s for s in signals if "TIME_EXIT" in s.reason]
        assert len(time_signals) == 0

    def test_time_exit_exactly_at_limit(self):
        """Time exit triggers at exactly max_hold_minutes."""
        pm = PositionManager()
        entry = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
        pos = _open_position(
            entry_price=97_500.0,
            stop_loss=96_037.50,
            entry_time=entry,
            metadata={"max_hold_minutes": 60},
        )

        ts = entry + timedelta(minutes=60)
        signals = pm.update_position(pos, current_price=97_600.0, timestamp=ts)
        time_signals = [s for s in signals if "TIME_EXIT" in s.reason]
        assert len(time_signals) == 1


# ---------------------------------------------------------------------------
# Closed position
# ---------------------------------------------------------------------------

class TestClosedPosition:
    """Test that closed positions generate no signals."""

    def test_closed_position_no_signals(self):
        """A closed position should produce no signals."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)
        pos.status = PositionStatus.CLOSED

        signals = pm.update_position(pos, current_price=50_000.0, timestamp=TS)
        assert signals == []


# ---------------------------------------------------------------------------
# PnL update
# ---------------------------------------------------------------------------

class TestPnlUpdate:
    """Test that PnL is updated on each tick."""

    def test_pnl_updated(self):
        """update_position should update current_pnl_pct."""
        pm = PositionManager()
        pos = _open_position(entry_price=97_500.0, stop_loss=96_037.50)

        pm.update_position(pos, current_price=98_000.0, timestamp=TS)

        expected_pnl = ((98_000.0 - 97_500.0) / 97_500.0) * 100.0
        assert pos.current_pnl_pct == pytest.approx(expected_pnl, rel=1e-4)
