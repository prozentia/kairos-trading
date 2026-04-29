"""Risk Analyst — evaluates risk factors: R/R, stop validity, exposure."""

from __future__ import annotations

import time

from core.models import MarketSnapshot, AgentSignal
from ai_agent.analysts.base_analyst import BaseAnalyst


class RiskAnalyst(BaseAnalyst):
    """Analyzes risk factors: stop loss validity, ATR-based distance,
    volatility environment, and position sizing feasibility."""

    name = "risk"

    async def analyze(self, snapshot: MarketSnapshot) -> AgentSignal:
        states = snapshot.indicator_states
        scores: list[float] = []

        # ATR z-score (normal volatility = good)
        atr_zscore = states.get("atr_zscore", 0.0)
        if atr_zscore < 1.0:
            scores.append(0.8)  # Normal volatility
        elif atr_zscore < 2.0:
            scores.append(0.6)  # Elevated
        elif atr_zscore < 3.0:
            scores.append(0.35)  # High
        else:
            scores.append(0.1)  # Extreme — avoid trading

        # ATR value for stop distance feasibility
        atr = states.get("atr_14", 0.0)
        price = snapshot.last_price
        if atr and price:
            atr_pct = (atr / price) * 100
            if 0.3 <= atr_pct <= 1.5:
                scores.append(0.8)  # Healthy ATR range
            elif atr_pct < 0.3:
                scores.append(0.5)  # Too tight, hard to set stops
            else:
                scores.append(0.3)  # Too wide, expensive stops

        # Spread risk
        if snapshot.spread_bps < 1.0:
            scores.append(0.85)
        elif snapshot.spread_bps < 2.0:
            scores.append(0.7)
        elif snapshot.spread_bps < 3.0:
            scores.append(0.5)
        else:
            scores.append(0.2)

        # Volume adequacy (need volume for clean fills)
        if snapshot.volume_ratio_vs_avg > 1.0:
            scores.append(0.75)
        elif snapshot.volume_ratio_vs_avg > 0.5:
            scores.append(0.5)
        else:
            scores.append(0.25)

        # Macro risk penalty
        if snapshot.macro_risk_score < 0.5:
            scores.append(0.7)
        elif snapshot.macro_risk_score < 0.7:
            scores.append(0.5)
        else:
            scores.append(0.2)

        final_score = sum(scores) / len(scores) if scores else 0.5

        return AgentSignal(
            agent=self.name,
            timestamp=int(time.time()),
            signal_score=max(0.0, min(1.0, final_score)),
            data={
                "atr_zscore": atr_zscore,
                "spread_bps": snapshot.spread_bps,
                "volume_ratio": snapshot.volume_ratio_vs_avg,
                "sub_scores": scores,
            },
        )
