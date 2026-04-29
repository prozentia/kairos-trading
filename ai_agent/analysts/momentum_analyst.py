"""Momentum Analyst — RSI, MACD, volume velocity, order book imbalance."""

from __future__ import annotations

import time

from core.models import MarketSnapshot, AgentSignal
from ai_agent.analysts.base_analyst import BaseAnalyst


class MomentumAnalyst(BaseAnalyst):
    """Analyzes momentum: RSI divergences, MACD crossovers,
    volume velocity, and rate of change."""

    name = "momentum"

    async def analyze(self, snapshot: MarketSnapshot) -> AgentSignal:
        states = snapshot.indicator_states
        scores: list[float] = []

        # RSI analysis
        rsi = states.get("rsi_14")
        if rsi is not None:
            if rsi > 70:
                scores.append(0.3)  # Overbought — caution
            elif rsi > 55:
                scores.append(0.8)  # Strong momentum
            elif rsi > 45:
                scores.append(0.5)  # Neutral
            elif rsi > 30:
                scores.append(0.35)  # Weak
            else:
                scores.append(0.2)  # Oversold

        # Volume ratio (above average = confirmation)
        vol_ratio = snapshot.volume_ratio_vs_avg
        if vol_ratio > 2.0:
            scores.append(0.9)
        elif vol_ratio > 1.5:
            scores.append(0.75)
        elif vol_ratio > 1.0:
            scores.append(0.6)
        elif vol_ratio > 0.5:
            scores.append(0.4)
        else:
            scores.append(0.2)

        # MACD histogram momentum
        macd_hist = states.get("macd_histogram")
        macd_prev = states.get("macd_histogram_prev")
        if macd_hist is not None:
            if macd_hist > 0:
                scores.append(0.7)
                if macd_prev is not None and macd_hist > macd_prev:
                    scores.append(0.8)  # Accelerating
            else:
                scores.append(0.3)

        # Rate of change
        roc = states.get("rate_of_change")
        if roc is not None:
            if roc > 0.5:
                scores.append(0.8)
            elif roc > 0:
                scores.append(0.6)
            elif roc > -0.5:
                scores.append(0.4)
            else:
                scores.append(0.2)

        # OBV trend
        obv_trend = states.get("obv_trend")
        if obv_trend is not None:
            if obv_trend == "up":
                scores.append(0.75)
            elif obv_trend == "down":
                scores.append(0.25)
            else:
                scores.append(0.5)

        final_score = sum(scores) / len(scores) if scores else 0.5

        return AgentSignal(
            agent=self.name,
            timestamp=int(time.time()),
            signal_score=max(0.0, min(1.0, final_score)),
            data={
                "rsi": rsi,
                "volume_ratio": vol_ratio,
                "macd_histogram": macd_hist,
                "sub_scores": scores,
            },
        )
