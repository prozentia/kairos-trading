"""Tests for core.risk.risk_gate — all 10 rules + integration."""

import time
import pytest
from core.models import (
    TradeProposal,
    MarketSnapshot,
    SessionState,
    RiskConfig,
    BotState,
)
from core.risk.risk_gate import RiskGate


def _default_snapshot(**overrides) -> MarketSnapshot:
    defaults = dict(
        timestamp=int(time.time()),
        symbol="BTCUSDT",
        last_price=84500.0,
        bid=84499.0,
        ask=84501.0,
        spread_bps=0.5,
        volume_1m=100.0,
        volume_ratio_vs_avg=1.2,
        macro_risk_score=0.3,
        indicator_states={"atr_zscore": 1.0},
    )
    defaults.update(overrides)
    return MarketSnapshot(**defaults)


def _default_proposal(**overrides) -> TradeProposal:
    defaults = dict(
        timestamp=int(time.time()),
        symbol="BTCUSDT",
        action="BUY",
        confidence=0.75,
        entry_price_ref=84500.0,
        stop_loss=84200.0,
        take_profit=85100.0,
        reward_risk_ratio=2.5,
        setup_type="breakout",
    )
    defaults.update(overrides)
    return TradeProposal(**defaults)


def _default_session(**overrides) -> SessionState:
    defaults = dict(
        date="2026-03-10",
        trades_today=2,
        pnl_today_pct=0.5,
        open_positions=0,
        total_exposure_pct=0.0,
    )
    defaults.update(overrides)
    return SessionState(**defaults)


class TestRiskGateApproved:
    def test_all_checks_pass(self):
        gate = RiskGate()
        result = gate.validate(_default_proposal(), _default_snapshot(), _default_session())
        assert result.gate_decision == "APPROVED"
        assert result.rejection_reason is None
        assert len(result.checks) == 10
        assert all(c["passed"] for c in result.checks.values())


class TestRG01Spread:
    def test_reject_high_spread(self):
        gate = RiskGate()
        snapshot = _default_snapshot(spread_bps=5.0)
        result = gate.validate(_default_proposal(), snapshot, _default_session())
        assert result.gate_decision == "REJECTED"
        assert "RG-01" in result.rejection_reason


class TestRG02Slippage:
    def test_reject_low_volume_slippage(self):
        gate = RiskGate()
        snapshot = _default_snapshot(spread_bps=4.0, volume_ratio_vs_avg=0.3)
        result = gate.validate(_default_proposal(), snapshot, _default_session())
        assert result.gate_decision == "REJECTED"


class TestRG03Confidence:
    def test_reject_low_confidence(self):
        gate = RiskGate()
        proposal = _default_proposal(confidence=0.3)
        result = gate.validate(proposal, _default_snapshot(), _default_session())
        assert result.gate_decision == "REJECTED"
        assert "RG-03" in result.rejection_reason


class TestRG04RewardRisk:
    def test_reject_low_rr(self):
        gate = RiskGate()
        proposal = _default_proposal(reward_risk_ratio=1.0)
        result = gate.validate(proposal, _default_snapshot(), _default_session())
        assert result.gate_decision == "REJECTED"
        assert "RG-04" in result.rejection_reason


class TestRG05DailyDrawdown:
    def test_reject_daily_loss(self):
        gate = RiskGate()
        session = _default_session(pnl_today_pct=-3.0)
        result = gate.validate(_default_proposal(), _default_snapshot(), session)
        assert result.gate_decision == "REJECTED"
        assert "RG-05" in result.rejection_reason


class TestRG06MaxTrades:
    def test_reject_max_trades(self):
        gate = RiskGate()
        session = _default_session(trades_today=10)
        result = gate.validate(_default_proposal(), _default_snapshot(), session)
        assert result.gate_decision == "REJECTED"
        assert "RG-06" in result.rejection_reason


class TestRG07OpenPositions:
    def test_reject_max_positions(self):
        gate = RiskGate()
        session = _default_session(open_positions=1)
        result = gate.validate(_default_proposal(), _default_snapshot(), session)
        assert result.gate_decision == "REJECTED"
        assert "RG-07" in result.rejection_reason


class TestRG08Exposure:
    def test_reject_high_exposure(self):
        gate = RiskGate()
        session = _default_session(total_exposure_pct=2.0)
        result = gate.validate(_default_proposal(), _default_snapshot(), session)
        assert result.gate_decision == "REJECTED"
        assert "RG-08" in result.rejection_reason


class TestRG09Volatility:
    def test_reject_high_volatility(self):
        gate = RiskGate()
        snapshot = _default_snapshot(indicator_states={"atr_zscore": 4.0})
        result = gate.validate(_default_proposal(), snapshot, _default_session())
        assert result.gate_decision == "REJECTED"
        assert "RG-09" in result.rejection_reason


class TestRG10MacroRisk:
    def test_reject_high_macro_risk(self):
        gate = RiskGate()
        snapshot = _default_snapshot(macro_risk_score=0.9)
        result = gate.validate(_default_proposal(), snapshot, _default_session())
        assert result.gate_decision == "REJECTED"
        assert "RG-10" in result.rejection_reason


class TestRiskGateCustomConfig:
    def test_custom_config_allows_higher_spread(self):
        config = RiskConfig(max_spread_bps=10.0)
        gate = RiskGate(config)
        snapshot = _default_snapshot(spread_bps=5.0)
        result = gate.validate(_default_proposal(), snapshot, _default_session())
        assert result.checks["RG-01"]["passed"] is True
