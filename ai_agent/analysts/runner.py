"""Run all analyst agents in parallel and collect their signals."""

from __future__ import annotations

import asyncio

from core.models import MarketSnapshot, AgentSignal
from ai_agent.analysts.technical_analyst import TechnicalAnalyst
from ai_agent.analysts.momentum_analyst import MomentumAnalyst
from ai_agent.analysts.context_analyst import ContextAnalyst
from ai_agent.analysts.risk_analyst import RiskAnalyst


async def run_analysts(snapshot: MarketSnapshot) -> list[AgentSignal]:
    """Launch all 4 analysts in parallel and return their signals.

    Args:
        snapshot: Current market state.

    Returns:
        List of AgentSignal from each analyst.
    """
    analysts = [
        TechnicalAnalyst(),
        MomentumAnalyst(),
        ContextAnalyst(),
        RiskAnalyst(),
    ]

    signals = await asyncio.gather(
        *[a.analyze(snapshot) for a in analysts],
        return_exceptions=True,
    )

    # Filter out exceptions, log them in production
    valid_signals: list[AgentSignal] = []
    for s in signals:
        if isinstance(s, AgentSignal):
            valid_signals.append(s)

    return valid_signals
