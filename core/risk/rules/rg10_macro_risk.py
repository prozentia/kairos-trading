"""RG-10: Macro risk — reject if macro risk score is too high."""

from core.models import MarketSnapshot, RiskConfig
from core.risk.rules.common import RuleResult


def check(snapshot: MarketSnapshot, config: RiskConfig) -> RuleResult:
    passed = snapshot.macro_risk_score <= config.max_macro_risk_score
    return RuleResult(
        rule_id="RG-10",
        rule_name="macro_risk",
        passed=passed,
        value=round(snapshot.macro_risk_score, 2),
        threshold=config.max_macro_risk_score,
        reason="" if passed else f"Macro risk {snapshot.macro_risk_score:.2f} exceeds max {config.max_macro_risk_score:.2f}",
    )
