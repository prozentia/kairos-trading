"""Tests for portfolio-level risk management.

Covers position gating, circuit breakers, daily statistics,
exposure calculation, and correlation checking.
"""

from datetime import datetime, timezone

import pytest

from core.models import Position, PositionStatus, RiskLimits, Trade
from core.risk.portfolio import PortfolioManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def limits() -> RiskLimits:
    return RiskLimits(
        max_positions=3,
        max_exposure_pct=50.0,
        max_daily_loss_pct=5.0,
        max_drawdown_pct=15.0,
        position_size_pct=10.0,
        max_daily_trades=10,
    )


@pytest.fixture
def pm(limits: RiskLimits) -> PortfolioManager:
    return PortfolioManager(limits)


def _position(pair: str = "BTC/USDT", qty: float = 0.001, entry: float = 97_500.0) -> Position:
    return Position(
        pair=pair,
        side="BUY",
        entry_price=entry,
        quantity=qty,
        entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        status=PositionStatus.OPEN,
    )


def _trade(pnl: float = 1.0) -> Trade:
    return Trade(
        pair="BTC/USDT",
        side="BUY",
        entry_price=97_500.0,
        exit_price=97_500.0 + pnl * 100,
        quantity=0.001,
        entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        exit_time=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
        pnl_usdt=pnl,
    )


# ---------------------------------------------------------------------------
# can_open_position
# ---------------------------------------------------------------------------

class TestCanOpenPosition:
    """Test position gating checks."""

    def test_allowed_when_below_limits(self, pm: PortfolioManager):
        positions = [_position()]
        allowed, reason = pm.can_open_position(positions, balance=10_000.0)
        assert allowed is True
        assert reason == ""

    def test_blocked_at_max_positions(self, pm: PortfolioManager):
        positions = [_position() for _ in range(3)]
        allowed, reason = pm.can_open_position(positions, balance=10_000.0)
        assert allowed is False
        assert "Max positions" in reason

    def test_blocked_at_max_daily_trades(self, pm: PortfolioManager):
        allowed, reason = pm.can_open_position(
            [], balance=10_000.0, daily_trade_count=10,
        )
        assert allowed is False
        assert "daily trades" in reason.lower()

    def test_blocked_at_daily_loss_limit(self, pm: PortfolioManager):
        allowed, reason = pm.can_open_position(
            [], balance=10_000.0, daily_pnl_pct=-5.0,
        )
        assert allowed is False
        assert "loss limit" in reason.lower()

    def test_loss_just_below_limit(self, pm: PortfolioManager):
        """Loss just below the threshold should still allow."""
        allowed, _ = pm.can_open_position(
            [], balance=10_000.0, daily_pnl_pct=-4.9,
        )
        assert allowed is True

    def test_blocked_zero_balance(self, pm: PortfolioManager):
        allowed, reason = pm.can_open_position([], balance=0.0)
        assert allowed is False
        assert "capital" in reason.lower()

    def test_empty_positions_allowed(self, pm: PortfolioManager):
        allowed, _ = pm.can_open_position([], balance=10_000.0)
        assert allowed is True


# ---------------------------------------------------------------------------
# Circuit breakers
# ---------------------------------------------------------------------------

class TestCircuitBreakers:
    """Test circuit breaker logic."""

    def test_no_breaker_normal_conditions(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(0.5), _trade(-0.3)]
        ok, reason = pm.check_circuit_breakers(trades, daily_pnl_pct=-1.0, capital=1000.0)
        assert ok is True

    def test_three_consecutive_losses(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(-0.5), _trade(-0.3), _trade(-0.2)]
        ok, reason = pm.check_circuit_breakers(trades, daily_pnl_pct=-1.0, capital=1000.0)
        assert ok is False
        assert "consecutive losses" in reason.lower()

    def test_two_consecutive_losses_ok(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(-0.5), _trade(-0.3)]
        ok, _ = pm.check_circuit_breakers(trades, daily_pnl_pct=-0.8, capital=1000.0)
        assert ok is True

    def test_10_percent_daily_loss(self, pm: PortfolioManager):
        ok, reason = pm.check_circuit_breakers([], daily_pnl_pct=-10.0, capital=1000.0)
        assert ok is False
        assert "daily loss" in reason.lower()

    def test_capital_exhausted(self, pm: PortfolioManager):
        """Capital exhaustion should trip the breaker (when daily loss < 10%)."""
        trades = [_trade(-5.0)]
        ok, reason = pm.check_circuit_breakers(trades, daily_pnl_pct=-5.0, capital=0.0)
        assert ok is False
        assert "capital exhausted" in reason.lower()

    def test_no_trades_no_capital_ok(self, pm: PortfolioManager):
        """No trades + zero capital should not trip the capital breaker."""
        ok, _ = pm.check_circuit_breakers([], daily_pnl_pct=0.0, capital=0.0)
        assert ok is True


# ---------------------------------------------------------------------------
# Daily statistics
# ---------------------------------------------------------------------------

class TestDailyStats:
    """Test daily statistics calculation."""

    def test_empty_trades(self, pm: PortfolioManager):
        stats = pm.calculate_daily_stats([])
        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["total_pnl"] == 0.0

    def test_all_winners(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(2.0), _trade(0.5)]
        stats = pm.calculate_daily_stats(trades)
        assert stats["total_trades"] == 3
        assert stats["wins"] == 3
        assert stats["losses"] == 0
        assert stats["win_rate"] == pytest.approx(100.0)
        assert stats["total_pnl"] == pytest.approx(3.5)
        assert stats["max_win"] == pytest.approx(2.0)
        assert stats["max_loss"] == 0.0

    def test_mixed_results(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(-0.5), _trade(2.0), _trade(-1.0)]
        stats = pm.calculate_daily_stats(trades)
        assert stats["total_trades"] == 4
        assert stats["wins"] == 2
        assert stats["losses"] == 2
        assert stats["win_rate"] == pytest.approx(50.0)
        assert stats["total_pnl"] == pytest.approx(1.5)
        assert stats["max_win"] == pytest.approx(2.0)
        assert stats["max_loss"] == pytest.approx(-1.0)

    def test_profit_factor(self, pm: PortfolioManager):
        trades = [_trade(3.0), _trade(-1.0)]
        stats = pm.calculate_daily_stats(trades)
        assert stats["profit_factor"] == pytest.approx(3.0)

    def test_profit_factor_no_losses(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(2.0)]
        stats = pm.calculate_daily_stats(trades)
        assert stats["profit_factor"] == float("inf")

    def test_max_drawdown(self, pm: PortfolioManager):
        """Drawdown should track peak-to-trough of cumulative PnL."""
        trades = [_trade(3.0), _trade(-1.0), _trade(-1.5), _trade(2.0)]
        stats = pm.calculate_daily_stats(trades)
        # Cumulative: 3, 2, 0.5, 2.5
        # Peak = 3, trough = 0.5, max_dd = 2.5
        assert stats["max_drawdown"] == pytest.approx(2.5)

    def test_sharpe_positive(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(2.0), _trade(1.5)]
        stats = pm.calculate_daily_stats(trades)
        assert stats["sharpe"] > 0


# ---------------------------------------------------------------------------
# Exposure
# ---------------------------------------------------------------------------

class TestExposure:
    """Test exposure calculation."""

    def test_single_position(self, pm: PortfolioManager):
        positions = [_position(pair="BTC/USDT", qty=0.001, entry=97_500.0)]
        prices = {"BTC/USDT": 98_000.0}
        exposure = pm.get_exposure(positions, prices)
        assert exposure["total_exposure"] == pytest.approx(0.001 * 98_000.0)
        assert exposure["position_count"] == 1
        assert "BTC/USDT" in exposure["per_pair"]

    def test_multiple_positions(self, pm: PortfolioManager):
        positions = [
            _position(pair="BTC/USDT", qty=0.001, entry=97_500.0),
            _position(pair="ETH/USDT", qty=0.1, entry=2_500.0),
        ]
        prices = {"BTC/USDT": 98_000.0, "ETH/USDT": 2_600.0}
        exposure = pm.get_exposure(positions, prices)
        expected = (0.001 * 98_000.0) + (0.1 * 2_600.0)
        assert exposure["total_exposure"] == pytest.approx(expected)
        assert exposure["position_count"] == 2

    def test_closed_positions_excluded(self, pm: PortfolioManager):
        pos = _position()
        pos.status = PositionStatus.CLOSED
        exposure = pm.get_exposure([pos], {"BTC/USDT": 98_000.0})
        assert exposure["total_exposure"] == 0.0
        assert exposure["position_count"] == 0

    def test_fallback_to_entry_price(self, pm: PortfolioManager):
        """When current price is missing, use entry price."""
        positions = [_position(pair="BTC/USDT", qty=0.001, entry=97_500.0)]
        exposure = pm.get_exposure(positions, {})
        assert exposure["total_exposure"] == pytest.approx(0.001 * 97_500.0)


# ---------------------------------------------------------------------------
# Correlation check
# ---------------------------------------------------------------------------

class TestCorrelation:
    """Test correlation checking."""

    def test_high_correlation_warned(self, pm: PortfolioManager):
        positions = [
            _position(pair="BTC/USDT"),
            _position(pair="ETH/USDT"),
        ]
        corr = {("BTC/USDT", "ETH/USDT"): 0.85}
        ok, reason = pm.check_correlation(positions, corr, threshold=0.8)
        assert ok is False
        assert "correlation" in reason.lower()

    def test_low_correlation_ok(self, pm: PortfolioManager):
        positions = [
            _position(pair="BTC/USDT"),
            _position(pair="SOL/USDT"),
        ]
        corr = {("BTC/USDT", "SOL/USDT"): 0.5}
        ok, _ = pm.check_correlation(positions, corr, threshold=0.8)
        assert ok is True

    def test_single_position_ok(self, pm: PortfolioManager):
        ok, _ = pm.check_correlation([_position()], {("BTC/USDT", "ETH/USDT"): 0.9})
        assert ok is True

    def test_no_correlation_matrix(self, pm: PortfolioManager):
        positions = [_position(), _position(pair="ETH/USDT")]
        ok, _ = pm.check_correlation(positions, None)
        assert ok is True

    def test_reverse_key_order(self, pm: PortfolioManager):
        """Correlation matrix with reversed key order should still match."""
        positions = [
            _position(pair="BTC/USDT"),
            _position(pair="ETH/USDT"),
        ]
        corr = {("ETH/USDT", "BTC/USDT"): 0.9}
        ok, _ = pm.check_correlation(positions, corr, threshold=0.8)
        assert ok is False


# ---------------------------------------------------------------------------
# Consecutive losses helper
# ---------------------------------------------------------------------------

class TestConsecutiveLosses:
    """Test the consecutive losses counting utility."""

    def test_three_losses(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(-1.0), _trade(-1.0), _trade(-1.0)]
        assert pm._count_consecutive_losses(trades) == 3

    def test_broken_by_win(self, pm: PortfolioManager):
        trades = [_trade(-1.0), _trade(-1.0), _trade(1.0), _trade(-1.0)]
        assert pm._count_consecutive_losses(trades) == 1

    def test_no_trades(self, pm: PortfolioManager):
        assert pm._count_consecutive_losses([]) == 0

    def test_all_wins(self, pm: PortfolioManager):
        trades = [_trade(1.0), _trade(2.0)]
        assert pm._count_consecutive_losses(trades) == 0
