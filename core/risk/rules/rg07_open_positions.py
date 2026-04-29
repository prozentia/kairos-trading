"""RG-07: Open positions — reject if max concurrent positions reached."""

from core.models import SessionState, RiskConfig
from core.risk.rules.common import RuleResult


def check(session: SessionState, config: RiskConfig) -> RuleResult:
    passed = session.open_positions < config.max_concurrent_positions
    return RuleResult(
        rule_id="RG-07",
        rule_name="open_positions",
        passed=passed,
        value=session.open_positions,
        threshold=config.max_concurrent_positions,
        reason="" if passed else f"Open positions {session.open_positions} reached max {config.max_concurrent_positions}",
    )
