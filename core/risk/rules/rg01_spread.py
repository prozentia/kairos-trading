"""RG-01: Spread check — reject if bid/ask spread is too wide."""

from core.models import MarketSnapshot, RiskConfig
from core.risk.rules.common import RuleResult


def check(snapshot: MarketSnapshot, config: RiskConfig) -> RuleResult:
    passed = snapshot.spread_bps <= config.max_spread_bps
    return RuleResult(
        rule_id="RG-01",
        rule_name="spread_check",
        passed=passed,
        value=snapshot.spread_bps,
        threshold=config.max_spread_bps,
        reason="" if passed else f"Spread {snapshot.spread_bps:.1f} bps exceeds max {config.max_spread_bps:.1f} bps",
    )
