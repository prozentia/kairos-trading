"""RG-09: Volatility filter — reject if ATR z-score indicates abnormal volatility."""

from core.models import MarketSnapshot, RiskConfig
from core.risk.rules.common import RuleResult


def check(snapshot: MarketSnapshot, config: RiskConfig) -> RuleResult:
    atr_zscore = snapshot.indicator_states.get("atr_zscore", 0.0)
    passed = atr_zscore <= config.max_atr_zscore
    return RuleResult(
        rule_id="RG-09",
        rule_name="volatility_filter",
        passed=passed,
        value=round(atr_zscore, 2),
        threshold=config.max_atr_zscore,
        reason="" if passed else f"ATR z-score {atr_zscore:.2f} exceeds max {config.max_atr_zscore:.2f}",
    )
