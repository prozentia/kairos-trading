"""Context Analyst — market regime, funding, session, macro factors."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from core.models import MarketSnapshot, AgentSignal
from ai_agent.analysts.base_analyst import BaseAnalyst


class ContextAnalyst(BaseAnalyst):
    """Analyzes market context: trading session, funding rate,
    open interest, macro risk, and market regime."""

    name = "context"

    async def analyze(self, snapshot: MarketSnapshot) -> AgentSignal:
        scores: list[float] = []

        # Funding rate (negative = shorts paying longs = bullish for longs)
        funding = snapshot.funding_rate
        if funding < -0.01:
            scores.append(0.8)  # Very negative = bullish
        elif funding < 0:
            scores.append(0.65)
        elif funding < 0.01:
            scores.append(0.5)  # Neutral
        elif funding < 0.03:
            scores.append(0.35)
        else:
            scores.append(0.2)  # High positive = crowded long

        # Open interest trend
        oi = snapshot.open_interest
        if oi > 0:
            scores.append(0.6)  # OI present, market active
        else:
            scores.append(0.4)

        # Macro risk score (lower = better for longs)
        macro = snapshot.macro_risk_score
        if macro < 0.3:
            scores.append(0.8)
        elif macro < 0.5:
            scores.append(0.6)
        elif macro < 0.7:
            scores.append(0.4)
        else:
            scores.append(0.2)

        # Trading session (best volumes during London+NY overlap)
        session_score = self._session_score()
        scores.append(session_score)

        # Spread as liquidity indicator
        if snapshot.spread_bps < 1.0:
            scores.append(0.8)  # Tight spread = good liquidity
        elif snapshot.spread_bps < 2.0:
            scores.append(0.6)
        elif snapshot.spread_bps < 5.0:
            scores.append(0.4)
        else:
            scores.append(0.2)

        final_score = sum(scores) / len(scores) if scores else 0.5

        return AgentSignal(
            agent=self.name,
            timestamp=int(time.time()),
            signal_score=max(0.0, min(1.0, final_score)),
            data={
                "funding_rate": funding,
                "macro_risk": macro,
                "session": self._current_session(),
                "spread_bps": snapshot.spread_bps,
                "sub_scores": scores,
            },
        )

    @staticmethod
    def _session_score() -> float:
        """Score based on current trading session."""
        hour = datetime.now(timezone.utc).hour
        # London + NY overlap (13-17 UTC) = best
        if 13 <= hour <= 17:
            return 0.85
        # London (7-16 UTC) or NY (13-22 UTC)
        if 7 <= hour <= 22:
            return 0.65
        # Asian session (0-8 UTC)
        if 0 <= hour <= 8:
            return 0.5
        return 0.4

    @staticmethod
    def _current_session() -> str:
        hour = datetime.now(timezone.utc).hour
        if 13 <= hour <= 17:
            return "london_ny_overlap"
        if 7 <= hour <= 16:
            return "london"
        if 13 <= hour <= 22:
            return "new_york"
        return "asian"
