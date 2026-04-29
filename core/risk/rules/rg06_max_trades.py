"""RG-06: Max trades per day — reject if daily trade count exceeded."""

from core.models import SessionState, RiskConfig
from core.risk.rules.common import RuleResult


def check(session: SessionState, config: RiskConfig) -> RuleResult:
    passed = session.trades_today < config.max_trades_per_day
    return RuleResult(
        rule_id="RG-06",
        rule_name="max_daily_trades",
        passed=passed,
        value=session.trades_today,
        threshold=config.max_trades_per_day,
        reason="" if passed else f"Trades today {session.trades_today} reached max {config.max_trades_per_day}",
    )
