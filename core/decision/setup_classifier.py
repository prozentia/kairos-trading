"""Classify market setup type from indicator states."""

from __future__ import annotations

from typing import Any


SETUP_BREAKOUT = "breakout"
SETUP_PULLBACK = "pullback"
SETUP_CONSOLIDATION_EXIT = "consolidation_exit"
SETUP_MEAN_REVERSION = "mean_reversion"
SETUP_TREND_FOLLOWING = "trend_following"
SETUP_UNKNOWN = "unknown"


def classify_setup(indicator_states: dict[str, Any]) -> str:
    """Classify the current market setup based on indicator states.

    Args:
        indicator_states: Dict of indicator name -> computed value/state.
            Expected keys (all optional, gracefully degrades):
            - ema_9, ema_21, ema_50, ema_200: EMA values
            - rsi_14: RSI value
            - atr_14: ATR value
            - volume_ratio: current vol / avg vol
            - higher_highs: bool — is market making higher highs
            - higher_lows: bool — is market making higher lows
            - price: current price
            - macd_histogram: MACD histogram value
            - bollinger_upper, bollinger_lower: Bollinger bands

    Returns:
        Setup type string.
    """
    price = indicator_states.get("price", 0.0)
    ema_9 = indicator_states.get("ema_9", 0.0)
    ema_21 = indicator_states.get("ema_21", 0.0)
    ema_50 = indicator_states.get("ema_50", 0.0)
    ema_200 = indicator_states.get("ema_200", 0.0)
    rsi = indicator_states.get("rsi_14", 50.0)
    volume_ratio = indicator_states.get("volume_ratio", 1.0)
    higher_highs = indicator_states.get("higher_highs", False)
    higher_lows = indicator_states.get("higher_lows", False)
    macd_hist = indicator_states.get("macd_histogram", 0.0)
    bb_upper = indicator_states.get("bollinger_upper", 0.0)
    bb_lower = indicator_states.get("bollinger_lower", 0.0)

    if not price or not ema_9:
        return SETUP_UNKNOWN

    ema_aligned_bull = ema_9 > ema_21 > ema_50 if ema_9 and ema_21 and ema_50 else False
    trend_up = higher_highs and higher_lows

    # Breakout: price above all EMAs, high volume, strong momentum
    if (ema_aligned_bull
            and volume_ratio > 1.5
            and rsi > 55
            and macd_hist > 0
            and price > ema_9):
        return SETUP_BREAKOUT

    # Pullback: uptrend but price pulled back to EMA support
    if (trend_up
            and ema_aligned_bull
            and price <= ema_21 * 1.005
            and price >= ema_50 * 0.995
            and rsi < 45
            and rsi > 30):
        return SETUP_PULLBACK

    # Mean reversion: RSI oversold, price near lower Bollinger
    if bb_lower and price:
        near_bb_lower = price <= bb_lower * 1.01
        if rsi < 30 and near_bb_lower and volume_ratio > 1.2:
            return SETUP_MEAN_REVERSION

    # Consolidation exit: tight range breaking out
    if bb_upper and bb_lower:
        bb_width = (bb_upper - bb_lower) / price if price else 0
        if bb_width < 0.02 and volume_ratio > 2.0 and price > bb_upper:
            return SETUP_CONSOLIDATION_EXIT

    # Trend following: aligned EMAs, moderate momentum
    if ema_aligned_bull and trend_up and rsi > 50 and rsi < 70:
        return SETUP_TREND_FOLLOWING

    return SETUP_UNKNOWN
