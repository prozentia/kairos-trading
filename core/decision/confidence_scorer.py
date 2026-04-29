"""Compute a composite confidence score for a trade proposal."""

from __future__ import annotations

from typing import Any

from core.models import AgentSignal


def compute_confidence(
    signals: list[AgentSignal],
    setup_type: str,
    indicator_states: dict[str, Any],
) -> float:
    """Compute a confidence score from 0 to 100.

    Factors:
    - Agent consensus (40%): how aligned are the agents
    - Setup quality (25%): known setups score higher
    - Multi-timeframe alignment (20%): EMAs aligned across timeframes
    - Indicator convergence (15%): momentum + trend agreement

    Args:
        signals: Agent signals with scores 0.0–1.0.
        setup_type: Classified setup type.
        indicator_states: Current indicator values.

    Returns:
        Confidence score between 0 and 100.
    """
    agent_score = _agent_consensus_score(signals)
    setup_score = _setup_quality_score(setup_type)
    mtf_score = _multi_timeframe_score(indicator_states)
    convergence_score = _indicator_convergence_score(indicator_states)

    raw = (
        agent_score * 0.40
        + setup_score * 0.25
        + mtf_score * 0.20
        + convergence_score * 0.15
    )

    return round(max(0.0, min(100.0, raw)), 1)


def _agent_consensus_score(signals: list[AgentSignal]) -> float:
    """Score based on how aligned agent signals are (0-100)."""
    if not signals:
        return 0.0

    scores = [max(0.0, min(1.0, s.signal_score)) for s in signals]
    avg = sum(scores) / len(scores)

    if len(scores) < 2:
        return avg * 100.0

    # Penalize disagreement via standard deviation
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5

    # High avg + low std = high consensus
    consensus_penalty = std_dev * 50.0  # max penalty ~25 points
    return max(0.0, avg * 100.0 - consensus_penalty)


_SETUP_QUALITY: dict[str, float] = {
    "breakout": 85.0,
    "pullback": 80.0,
    "trend_following": 75.0,
    "consolidation_exit": 70.0,
    "mean_reversion": 60.0,
    "unknown": 30.0,
}


def _setup_quality_score(setup_type: str) -> float:
    """Score based on historical reliability of setup type (0-100)."""
    return _SETUP_QUALITY.get(setup_type, 30.0)


def _multi_timeframe_score(indicator_states: dict[str, Any]) -> float:
    """Score based on EMA alignment across timeframes (0-100).

    Checks if higher timeframe EMAs confirm the direction.
    """
    price = indicator_states.get("price", 0.0)
    if not price:
        return 50.0

    alignment_checks = 0
    alignment_passes = 0

    for ema_key in ("ema_9", "ema_21", "ema_50", "ema_200"):
        val = indicator_states.get(ema_key, 0.0)
        if val:
            alignment_checks += 1
            if price > val:
                alignment_passes += 1

    if alignment_checks == 0:
        return 50.0

    ratio = alignment_passes / alignment_checks
    return ratio * 100.0


def _indicator_convergence_score(indicator_states: dict[str, Any]) -> float:
    """Score based on how many indicators agree on direction (0-100)."""
    bullish_signals = 0
    total_signals = 0

    # RSI
    rsi = indicator_states.get("rsi_14")
    if rsi is not None:
        total_signals += 1
        if 50 < rsi < 70:
            bullish_signals += 1

    # MACD
    macd_hist = indicator_states.get("macd_histogram")
    if macd_hist is not None:
        total_signals += 1
        if macd_hist > 0:
            bullish_signals += 1

    # Volume
    vol_ratio = indicator_states.get("volume_ratio")
    if vol_ratio is not None:
        total_signals += 1
        if vol_ratio > 1.0:
            bullish_signals += 1

    # Higher highs/lows
    hh = indicator_states.get("higher_highs")
    hl = indicator_states.get("higher_lows")
    if hh is not None:
        total_signals += 1
        if hh:
            bullish_signals += 1
    if hl is not None:
        total_signals += 1
        if hl:
            bullish_signals += 1

    if total_signals == 0:
        return 50.0

    return (bullish_signals / total_signals) * 100.0
