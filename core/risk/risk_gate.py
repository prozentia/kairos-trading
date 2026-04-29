"""Risk Gate — validates a trade proposal through 10 sequential rule checks."""

from __future__ import annotations

from core.models import (
    TradeProposal,
    MarketSnapshot,
    SessionState,
    RiskConfig,
    RiskGateResult,
)
from core.risk.rules.common import RuleResult
from core.risk.rules import (
    rg01_spread,
    rg02_slippage,
    rg03_confidence,
    rg04_reward_risk,
    rg05_daily_drawdown,
    rg06_max_trades,
    rg07_open_positions,
    rg08_exposure,
    rg09_volatility,
    rg10_macro_risk,
)


class RiskGate:
    """Run all 10 risk gate checks and return a consolidated result."""

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()

    def validate(
        self,
        proposal: TradeProposal,
        snapshot: MarketSnapshot,
        session: SessionState | None = None,
    ) -> RiskGateResult:
        """Run all risk checks against the proposal.

        Returns:
            RiskGateResult with gate_decision "APPROVED" or "REJECTED".
        """
        session = session or SessionState()
        checks: dict[str, dict] = {}
        first_rejection: str | None = None

        rules: list[RuleResult] = [
            rg01_spread.check(snapshot, self.config),
            rg02_slippage.check(snapshot, self.config),
            rg03_confidence.check(proposal, self.config),
            rg04_reward_risk.check(proposal, self.config),
            rg05_daily_drawdown.check(session, self.config),
            rg06_max_trades.check(session, self.config),
            rg07_open_positions.check(session, self.config),
            rg08_exposure.check(session, self.config),
            rg09_volatility.check(snapshot, self.config),
            rg10_macro_risk.check(snapshot, self.config),
        ]

        for rule in rules:
            checks[rule.rule_id] = {
                "rule_name": rule.rule_name,
                "passed": rule.passed,
                "value": rule.value,
                "threshold": rule.threshold,
                "reason": rule.reason,
            }
            if not rule.passed and first_rejection is None:
                first_rejection = f"{rule.rule_id} ({rule.rule_name}): {rule.reason}"

        return RiskGateResult(
            proposal_id=proposal.proposal_id,
            gate_decision="REJECTED" if first_rejection else "APPROVED",
            checks=checks,
            rejection_reason=first_rejection,
        )
