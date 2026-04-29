"""RG-02: Slippage estimate — reject if estimated slippage is too high."""

from core.models import MarketSnapshot, RiskConfig
from core.risk.rules.common import RuleResult


def check(snapshot: MarketSnapshot, config: RiskConfig) -> RuleResult:
    # Estimate slippage from spread and volume
    estimated_slippage = snapshot.spread_bps * 0.5
    if snapshot.volume_ratio_vs_avg < 0.5:
        estimated_slippage *= 2.0  # Low volume = higher slippage risk

    passed = estimated_slippage <= config.max_slippage_bps
    return RuleResult(
        rule_id="RG-02",
        rule_name="slippage_estimate",
        passed=passed,
        value=round(estimated_slippage, 2),
        threshold=config.max_slippage_bps,
        reason="" if passed else f"Estimated slippage {estimated_slippage:.1f} bps exceeds max {config.max_slippage_bps:.1f} bps",
    )
