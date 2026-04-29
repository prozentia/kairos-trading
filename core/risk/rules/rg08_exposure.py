"""RG-08: Exposure — reject if total exposure exceeds limit."""

from core.models import SessionState, RiskConfig
from core.risk.rules.common import RuleResult


def check(session: SessionState, config: RiskConfig) -> RuleResult:
    passed = session.total_exposure_pct < config.max_exposure_pct
    return RuleResult(
        rule_id="RG-08",
        rule_name="exposure",
        passed=passed,
        value=round(session.total_exposure_pct, 2),
        threshold=config.max_exposure_pct,
        reason="" if passed else f"Exposure {session.total_exposure_pct:.2f}% exceeds max {config.max_exposure_pct:.2f}%",
    )
