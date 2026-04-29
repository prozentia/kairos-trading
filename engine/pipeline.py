"""Trading pipeline — orchestrates the full analysis-to-execution flow.

Connects: MarketSnapshot -> AI Analysts -> Decision Engine -> Risk Gate -> Executor
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from core.models import (
    MarketSnapshot,
    TradeProposal,
    RiskConfig,
    SessionState,
    AgentSignal,
)
from core.decision.aggregator import aggregate
from core.decision.setup_classifier import classify_setup
from core.decision.confidence_scorer import compute_confidence
from core.risk.risk_gate import RiskGate
from ai_agent.analysts.runner import run_analysts
from engine.safety import SafetyManager

logger = logging.getLogger(__name__)

# Minimum confidence to generate a BUY proposal
MIN_AGGREGATE_SCORE = 0.55


class TradingPipeline:
    """Full trading pipeline from market data to trade proposal.

    Steps:
    1. Safety check
    2. Run AI analysts in parallel
    3. Aggregate signals
    4. Classify setup
    5. Score confidence
    6. Build trade proposal
    7. Risk gate validation
    """

    def __init__(
        self,
        risk_config: RiskConfig | None = None,
        safety: SafetyManager | None = None,
        min_score: float = MIN_AGGREGATE_SCORE,
    ) -> None:
        self._risk_config = risk_config or RiskConfig()
        self._risk_gate = RiskGate(self._risk_config)
        self._safety = safety or SafetyManager()
        self._min_score = min_score

    async def process(
        self,
        snapshot: MarketSnapshot,
        session: SessionState | None = None,
    ) -> dict[str, Any]:
        """Process a market snapshot through the full pipeline.

        Args:
            snapshot: Current market state.
            session: Current session state for risk checks.

        Returns:
            Dict with keys: action, proposal, gate_result, signals, reason.
        """
        session = session or SessionState()

        # 1. Safety check
        if self._safety.is_halted():
            return {
                "action": "HALTED",
                "reason": self._safety.halt_reason,
                "proposal": None,
                "gate_result": None,
                "signals": [],
            }

        # 2. Run AI analysts
        signals = await run_analysts(snapshot)
        if not signals:
            return {
                "action": "NO_SIGNAL",
                "reason": "No analyst signals produced",
                "proposal": None,
                "gate_result": None,
                "signals": [],
            }

        # 3. Aggregate scores
        agg_score = aggregate(signals)

        # 4. Classify setup
        setup_type = classify_setup(snapshot.indicator_states)

        # 5. Compute confidence
        confidence = compute_confidence(signals, setup_type, snapshot.indicator_states)

        # Below threshold — no trade
        if agg_score < self._min_score:
            return {
                "action": "NO_TRADE",
                "reason": f"Aggregate score {agg_score:.2f} below threshold {self._min_score}",
                "proposal": None,
                "gate_result": None,
                "signals": [s.to_dict() for s in signals],
                "aggregate_score": agg_score,
                "setup_type": setup_type,
                "confidence": confidence,
            }

        # 6. Build trade proposal
        entry = snapshot.last_price
        atr = snapshot.indicator_states.get("atr_14", entry * 0.003)
        stop_loss = entry - (atr * 1.5)
        take_profit = entry + (atr * 3.0)
        rr = (take_profit - entry) / (entry - stop_loss) if entry > stop_loss else 0.0

        proposal = TradeProposal(
            timestamp=int(time.time()),
            symbol=snapshot.symbol,
            action="BUY",
            confidence=confidence,
            entry_price_ref=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            reward_risk_ratio=round(rr, 2),
            setup_type=setup_type,
            reason=[f"Aggregate: {agg_score:.2f}", f"Setup: {setup_type}"],
            agent_scores={s.agent: round(s.signal_score, 3) for s in signals},
        )

        # 7. Risk gate
        gate_result = self._risk_gate.validate(proposal, snapshot, session)
        proposal.status = gate_result.gate_decision

        return {
            "action": gate_result.gate_decision,
            "proposal": proposal.to_dict(),
            "gate_result": gate_result.to_dict(),
            "signals": [s.to_dict() for s in signals],
            "aggregate_score": agg_score,
            "setup_type": setup_type,
            "confidence": confidence,
        }
