"""Technical Analyst — price structure, patterns, support/resistance."""

from __future__ import annotations

import time

from core.models import MarketSnapshot, AgentSignal
from ai_agent.analysts.base_analyst import BaseAnalyst


class TechnicalAnalyst(BaseAnalyst):
    """Analyzes price structure: EMA alignment, trend direction,
    support/resistance, and chart patterns."""

    name = "technical"

    async def analyze(self, snapshot: MarketSnapshot) -> AgentSignal:
        states = snapshot.indicator_states
        scores: list[float] = []

        # EMA alignment check (bullish: 9 > 21 > 50 > 200)
        ema_9 = states.get("ema_9", 0.0)
        ema_21 = states.get("ema_21", 0.0)
        ema_50 = states.get("ema_50", 0.0)
        ema_200 = states.get("ema_200", 0.0)

        if ema_9 and ema_21 and ema_50:
            if ema_9 > ema_21 > ema_50:
                scores.append(0.9)
            elif ema_9 > ema_21:
                scores.append(0.65)
            elif ema_9 < ema_21 < ema_50:
                scores.append(0.1)
            else:
                scores.append(0.4)

        # Price vs EMAs
        price = snapshot.last_price
        if price and ema_200:
            if price > ema_200:
                scores.append(0.7)
            else:
                scores.append(0.3)

        # Higher highs / higher lows (trend structure)
        hh = states.get("higher_highs", None)
        hl = states.get("higher_lows", None)
        if hh is not None and hl is not None:
            if hh and hl:
                scores.append(0.85)
            elif hh or hl:
                scores.append(0.55)
            else:
                scores.append(0.2)

        # MACD histogram direction
        macd_hist = states.get("macd_histogram")
        if macd_hist is not None:
            if macd_hist > 0:
                scores.append(0.7 + min(0.2, abs(macd_hist) * 10))
            else:
                scores.append(0.3 - min(0.2, abs(macd_hist) * 10))

        final_score = sum(scores) / len(scores) if scores else 0.5

        return AgentSignal(
            agent=self.name,
            timestamp=int(time.time()),
            signal_score=max(0.0, min(1.0, final_score)),
            data={
                "ema_aligned": ema_9 > ema_21 > ema_50 if all([ema_9, ema_21, ema_50]) else False,
                "above_ema200": price > ema_200 if ema_200 else None,
                "trend_structure": "bullish" if (hh and hl) else "bearish" if (not hh and not hl) else "mixed",
                "sub_scores": scores,
            },
        )
