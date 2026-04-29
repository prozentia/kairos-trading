"""Weighted score aggregation for AI analyst agent signals."""

from __future__ import annotations

from core.models import AgentSignal


AGENT_WEIGHTS: dict[str, float] = {
    "technical": 0.35,
    "momentum": 0.25,
    "context": 0.20,
    "risk": 0.20,
}


def aggregate(signals: list[AgentSignal], weights: dict[str, float] | None = None) -> float:
    """Combine agent signals into a single weighted score.

    Args:
        signals: List of AgentSignal from each analyst.
        weights: Optional custom weights. Defaults to AGENT_WEIGHTS.

    Returns:
        Weighted score between 0.0 and 1.0.
    """
    if not signals:
        return 0.0

    w = weights or AGENT_WEIGHTS
    total_weight = 0.0
    weighted_sum = 0.0

    for s in signals:
        agent_weight = w.get(s.agent, 0.0)
        score = max(0.0, min(1.0, s.signal_score))
        weighted_sum += score * agent_weight
        total_weight += agent_weight

    if total_weight == 0.0:
        return 0.0

    return weighted_sum / total_weight
