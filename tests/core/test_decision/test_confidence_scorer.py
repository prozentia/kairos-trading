"""Tests for core.decision.confidence_scorer."""

import time
import pytest
from core.models import AgentSignal
from core.decision.confidence_scorer import compute_confidence


def _make_signal(agent: str, score: float) -> AgentSignal:
    return AgentSignal(agent=agent, timestamp=int(time.time()), signal_score=score)


def test_confidence_empty_signals():
    result = compute_confidence([], "unknown", {})
    assert 0.0 <= result <= 100.0


def test_confidence_max_bullish():
    signals = [
        _make_signal("technical", 0.95),
        _make_signal("momentum", 0.90),
        _make_signal("context", 0.85),
        _make_signal("risk", 0.80),
    ]
    states = {
        "price": 105.0,
        "ema_9": 104.0,
        "ema_21": 103.0,
        "ema_50": 102.0,
        "ema_200": 100.0,
        "rsi_14": 60.0,
        "macd_histogram": 0.5,
        "volume_ratio": 1.5,
        "higher_highs": True,
        "higher_lows": True,
    }
    result = compute_confidence(signals, "breakout", states)
    assert result > 70.0


def test_confidence_bearish_signals():
    signals = [
        _make_signal("technical", 0.1),
        _make_signal("momentum", 0.2),
        _make_signal("context", 0.15),
        _make_signal("risk", 0.1),
    ]
    states = {
        "price": 95.0,
        "ema_9": 96.0,
        "ema_21": 97.0,
        "ema_50": 98.0,
        "rsi_14": 25.0,
        "macd_histogram": -0.5,
        "volume_ratio": 0.5,
        "higher_highs": False,
        "higher_lows": False,
    }
    result = compute_confidence(signals, "unknown", states)
    assert result < 30.0


def test_confidence_range_0_100():
    for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
        signals = [_make_signal("technical", score)]
        result = compute_confidence(signals, "unknown", {})
        assert 0.0 <= result <= 100.0


def test_confidence_setup_quality_matters():
    signals = [_make_signal("technical", 0.7)]
    states = {"price": 100.0, "ema_9": 99.0}

    breakout = compute_confidence(signals, "breakout", states)
    unknown = compute_confidence(signals, "unknown", states)
    assert breakout > unknown


def test_confidence_agent_consensus_rewards_alignment():
    aligned = [
        _make_signal("technical", 0.8),
        _make_signal("momentum", 0.8),
        _make_signal("context", 0.8),
        _make_signal("risk", 0.8),
    ]
    divergent = [
        _make_signal("technical", 1.0),
        _make_signal("momentum", 0.2),
        _make_signal("context", 0.9),
        _make_signal("risk", 0.1),
    ]
    states = {"price": 100.0}
    c_aligned = compute_confidence(aligned, "trend_following", states)
    c_divergent = compute_confidence(divergent, "trend_following", states)
    assert c_aligned > c_divergent


def test_confidence_multi_timeframe_all_above():
    signals = [_make_signal("technical", 0.7)]
    states = {
        "price": 105.0,
        "ema_9": 104.0,
        "ema_21": 103.0,
        "ema_50": 102.0,
        "ema_200": 100.0,
    }
    result = compute_confidence(signals, "trend_following", states)
    assert result > 50.0


def test_confidence_with_no_indicators():
    signals = [_make_signal("technical", 0.5)]
    result = compute_confidence(signals, "unknown", {})
    assert 0.0 <= result <= 100.0
