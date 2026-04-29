"""RG-04: Reward/risk ratio — reject if R:R is too low."""

from core.models import TradeProposal, RiskConfig
from core.risk.rules.common import RuleResult


def check(proposal: TradeProposal, config: RiskConfig) -> RuleResult:
    rr = proposal.reward_risk_ratio
    passed = rr >= config.min_reward_risk
    return RuleResult(
        rule_id="RG-04",
        rule_name="reward_risk_ratio",
        passed=passed,
        value=round(rr, 2),
        threshold=config.min_reward_risk,
        reason="" if passed else f"R:R {rr:.2f} below minimum {config.min_reward_risk:.2f}",
    )
