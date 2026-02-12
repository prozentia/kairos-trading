"""Tests for position sizing algorithms.

Covers fixed percentage, Kelly criterion, ATR-based sizing,
risk-based sizing, stop-loss/take-profit calculation, order validation,
and trust level adjustments.
"""

import pytest

from core.models import RiskLimits
from core.risk.sizing import PositionSizer, SymbolInfo, TRUST_LEVELS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_limits() -> RiskLimits:
    """Standard risk limits for testing."""
    return RiskLimits(
        max_positions=3,
        max_exposure_pct=50.0,
        max_daily_loss_pct=5.0,
        max_drawdown_pct=15.0,
        position_size_pct=10.0,
        max_daily_trades=20,
    )


@pytest.fixture
def sizer(default_limits: RiskLimits) -> PositionSizer:
    return PositionSizer(default_limits)


# ---------------------------------------------------------------------------
# Fixed percentage sizing
# ---------------------------------------------------------------------------

class TestFixedPercentage:
    """Test fixed percentage sizing."""

    def test_basic(self):
        result = PositionSizer.fixed_percentage(1000.0, 10.0)
        assert result == pytest.approx(100.0)

    def test_full_capital(self):
        result = PositionSizer.fixed_percentage(1000.0, 100.0)
        assert result == pytest.approx(1000.0)

    def test_zero_capital(self):
        assert PositionSizer.fixed_percentage(0.0, 10.0) == 0.0

    def test_zero_pct(self):
        assert PositionSizer.fixed_percentage(1000.0, 0.0) == 0.0

    def test_negative_capital(self):
        assert PositionSizer.fixed_percentage(-100.0, 10.0) == 0.0


# ---------------------------------------------------------------------------
# Kelly Criterion
# ---------------------------------------------------------------------------

class TestKellyCriterion:
    """Test Kelly Criterion sizing."""

    def test_profitable_system(self):
        """A system with positive expectancy should give positive size."""
        result = PositionSizer.kelly_criterion(
            win_rate=0.6, risk_reward=2.0, capital=1000.0, fraction=1.0,
        )
        # f* = (0.6 * 2.0 - 0.4) / 2.0 = (1.2 - 0.4) / 2.0 = 0.4
        assert result == pytest.approx(400.0)

    def test_half_kelly(self):
        """Half-Kelly should halve the position."""
        full = PositionSizer.kelly_criterion(
            win_rate=0.6, risk_reward=2.0, capital=1000.0, fraction=1.0,
        )
        half = PositionSizer.kelly_criterion(
            win_rate=0.6, risk_reward=2.0, capital=1000.0, fraction=0.5,
        )
        assert half == pytest.approx(full / 2.0)

    def test_negative_expectancy(self):
        """Negative expectancy should return 0."""
        result = PositionSizer.kelly_criterion(
            win_rate=0.3, risk_reward=1.0, capital=1000.0,
        )
        # f* = (0.3 * 1.0 - 0.7) / 1.0 = -0.4 < 0
        assert result == 0.0

    def test_zero_win_rate(self):
        assert PositionSizer.kelly_criterion(0.0, 2.0, 1000.0) == 0.0

    def test_zero_capital(self):
        assert PositionSizer.kelly_criterion(0.6, 2.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# ATR-based sizing
# ---------------------------------------------------------------------------

class TestAtrBased:
    """Test ATR-based position sizing."""

    def test_basic_atr(self):
        """Position size = risk_amount / ATR * price."""
        result = PositionSizer.atr_based(
            capital=10_000.0, atr=500.0, risk_pct=1.0, price=50_000.0,
        )
        # risk_amount = 10000 * 0.01 = 100
        # quantity = 100 / 500 = 0.2
        # size = 0.2 * 50000 = 10000
        assert result == pytest.approx(10_000.0)

    def test_high_volatility_smaller_position(self):
        """Higher ATR -> smaller position."""
        low_vol = PositionSizer.atr_based(1000.0, 100.0, 1.0, 1000.0)
        high_vol = PositionSizer.atr_based(1000.0, 200.0, 1.0, 1000.0)
        assert high_vol < low_vol

    def test_zero_atr(self):
        assert PositionSizer.atr_based(1000.0, 0.0, 1.0) == 0.0

    def test_zero_risk(self):
        assert PositionSizer.atr_based(1000.0, 100.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Risk-based sizing (calculate_size)
# ---------------------------------------------------------------------------

class TestCalculateSize:
    """Test risk-based position sizing."""

    def test_basic_calculation(self, sizer: PositionSizer):
        """Size = risk_amount / price_diff."""
        # balance=1000, position_size_pct=10%, risk_amount=100
        # entry=50000, sl=49000, diff=1000
        # quantity = 100 / 1000 = 0.1
        qty = sizer.calculate_size(
            balance=1000.0,
            entry_price=50_000.0,
            stop_loss_price=49_000.0,
        )
        assert qty == pytest.approx(0.1)

    def test_zero_balance(self, sizer: PositionSizer):
        assert sizer.calculate_size(0.0, 50_000.0, 49_000.0) == 0.0

    def test_same_entry_and_sl(self, sizer: PositionSizer):
        """Zero diff should return 0 (avoid division by zero)."""
        assert sizer.calculate_size(1000.0, 50_000.0, 50_000.0) == 0.0

    def test_with_symbol_info(self, sizer: PositionSizer):
        """Size should be clamped to symbol constraints."""
        info = SymbolInfo(min_qty=0.001, max_qty=10.0, step_size=0.001)
        qty = sizer.calculate_size(
            balance=1000.0,
            entry_price=50_000.0,
            stop_loss_price=49_000.0,
            symbol_info=info,
        )
        # 0.1 -> rounded to step 0.001 -> 0.1 (already aligned)
        assert qty == pytest.approx(0.1)

    def test_below_min_qty(self, sizer: PositionSizer):
        """Size below min_qty should return 0."""
        info = SymbolInfo(min_qty=1.0, max_qty=10.0, step_size=0.001)
        qty = sizer.calculate_size(
            balance=1000.0,
            entry_price=50_000.0,
            stop_loss_price=49_000.0,
            symbol_info=info,
        )
        assert qty == 0.0

    def test_clamped_to_max_qty(self, sizer: PositionSizer):
        """Size above max_qty should be clamped."""
        info = SymbolInfo(min_qty=0.0, max_qty=0.05, step_size=0.001)
        qty = sizer.calculate_size(
            balance=1000.0,
            entry_price=50_000.0,
            stop_loss_price=49_000.0,
            symbol_info=info,
        )
        assert qty == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Stop-loss calculation
# ---------------------------------------------------------------------------

class TestCalculateStopLoss:
    """Test ATR-based stop-loss calculation."""

    def test_basic_sl(self, sizer: PositionSizer):
        sl = sizer.calculate_stop_loss(50_000.0, atr_value=500.0, multiplier=2.0)
        # 50000 - 500*2 = 49000
        assert sl == pytest.approx(49_000.0)

    def test_sl_floor_at_zero(self, sizer: PositionSizer):
        """SL should never go below 0."""
        sl = sizer.calculate_stop_loss(100.0, atr_value=200.0, multiplier=2.0)
        assert sl == 0.0

    def test_zero_atr(self, sizer: PositionSizer):
        assert sizer.calculate_stop_loss(50_000.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Take-profit calculation
# ---------------------------------------------------------------------------

class TestCalculateTakeProfit:
    """Test risk/reward-based take-profit calculation."""

    def test_basic_tp(self, sizer: PositionSizer):
        tp = sizer.calculate_take_profit(50_000.0, stop_loss=49_000.0, risk_reward_ratio=2.0)
        # risk = 1000, tp = 50000 + 1000*2 = 52000
        assert tp == pytest.approx(52_000.0)

    def test_1_to_1_ratio(self, sizer: PositionSizer):
        tp = sizer.calculate_take_profit(50_000.0, stop_loss=49_000.0, risk_reward_ratio=1.0)
        assert tp == pytest.approx(51_000.0)

    def test_zero_price(self, sizer: PositionSizer):
        assert sizer.calculate_take_profit(0.0, 49_000.0, 2.0) == 0.0


# ---------------------------------------------------------------------------
# Order validation
# ---------------------------------------------------------------------------

class TestValidateOrder:
    """Test order validation logic."""

    def test_valid_order(self, sizer: PositionSizer):
        valid, reason = sizer.validate_order(balance=10_000.0, size=0.01, price=50_000.0)
        # notional = 500, balance = 10000, max_exposure = 5000 -> OK
        assert valid is True
        assert reason == ""

    def test_insufficient_balance(self, sizer: PositionSizer):
        valid, reason = sizer.validate_order(balance=100.0, size=0.01, price=50_000.0)
        assert valid is False
        assert "Insufficient" in reason

    def test_exceeds_exposure(self, sizer: PositionSizer):
        """Order that exceeds max exposure should be rejected."""
        valid, reason = sizer.validate_order(balance=10_000.0, size=0.2, price=50_000.0)
        # notional = 10000, max_exposure = 5000 -> rejected
        assert valid is False
        assert "exposure" in reason.lower()

    def test_zero_size(self, sizer: PositionSizer):
        valid, reason = sizer.validate_order(balance=10_000.0, size=0.0, price=50_000.0)
        assert valid is False

    def test_zero_price(self, sizer: PositionSizer):
        valid, reason = sizer.validate_order(balance=10_000.0, size=0.01, price=0.0)
        assert valid is False


# ---------------------------------------------------------------------------
# Trust level adjustment
# ---------------------------------------------------------------------------

class TestTrustLevel:
    """Test trust level position adjustment."""

    def test_crawl_zero_capital(self, sizer: PositionSizer):
        """CRAWL (0-40) should force 0% capital."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=20.0)
        assert adjusted == 0.0

    def test_walk_25_percent(self, sizer: PositionSizer):
        """WALK (40-65) should allow 25% capital."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=50.0)
        assert adjusted == pytest.approx(25.0)

    def test_run_50_percent(self, sizer: PositionSizer):
        """RUN (65-80) should allow 50% capital."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=70.0)
        assert adjusted == pytest.approx(50.0)

    def test_sprint_80_percent(self, sizer: PositionSizer):
        """SPRINT (80-100) should allow 80% capital."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=90.0)
        assert adjusted == pytest.approx(80.0)

    def test_exact_boundary_40(self, sizer: PositionSizer):
        """Score exactly at 40 should be WALK."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=40.0)
        assert adjusted == pytest.approx(25.0)

    def test_score_100(self, sizer: PositionSizer):
        """Score 100 should be SPRINT."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=100.0)
        assert adjusted == pytest.approx(80.0)

    def test_negative_score_clamped(self, sizer: PositionSizer):
        """Negative scores are clamped to 0 (CRAWL)."""
        adjusted = sizer.adjust_for_trust_level(100.0, trust_score=-10.0)
        assert adjusted == 0.0

    def test_zero_size(self, sizer: PositionSizer):
        """Zero size stays zero regardless of trust."""
        assert sizer.adjust_for_trust_level(0.0, trust_score=90.0) == 0.0
