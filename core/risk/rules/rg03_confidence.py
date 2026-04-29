"""RG-03: Confidence minimum — reject if confidence score is too low."""

from core.models import TradeProposal, RiskConfig
from core.risk.rules.common import RuleResult


def check(proposal: TradeProposal, config: RiskConfig) -> RuleResult:
    confidence_normalized = proposal.confidence / 100.0 if proposal.confidence > 1.0 else proposal.confidence
    passed = confidence_normalized >= config.min_confidence
    return RuleResult(
        rule_id="RG-03",
        rule_name="confidence_minimum",
        passed=passed,
        value=round(confidence_normalized, 3),
        threshold=config.min_confidence,
        reason="" if passed else f"Confidence {confidence_normalized:.2f} below minimum {config.min_confidence:.2f}",
    )
