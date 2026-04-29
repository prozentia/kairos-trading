"""RG-05: Daily drawdown — reject if daily loss limit exceeded."""

from core.models import SessionState, RiskConfig
from core.risk.rules.common import RuleResult


def check(session: SessionState, config: RiskConfig) -> RuleResult:
    loss = abs(min(0.0, session.pnl_today_pct))
    passed = loss < config.max_daily_loss_pct
    return RuleResult(
        rule_id="RG-05",
        rule_name="daily_drawdown",
        passed=passed,
        value=round(loss, 2),
        threshold=config.max_daily_loss_pct,
        reason="" if passed else f"Daily loss {loss:.2f}% exceeds max {config.max_daily_loss_pct:.2f}%",
    )
