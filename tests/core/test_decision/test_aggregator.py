"""Tests for core.decision.aggregator."""

import time
import pytest
from core.models import AgentSignal
from core.decision.aggregator import aggregate, AGENT_WEIGHTS


def _make_signal(agent: str, score: float) -> AgentSignal:
    return AgentSignal(agent=agent, timestamp=int(time.time()), signal_score=score)


def test_aggregate_empty_signals():
    assert aggregate([]) == 0.0


def test_aggregate_single_signal():
    signals = [_make_signal("technical", 0.8)]
    result = aggregate(signals)
    assert 0.0 <= result <= 1.0
    assert result == pytest.approx(0.8, abs=0.01)


def test_aggregate_all_agents_max():
    signals = [
        _make_signal("technical", 1.0),
        _make_signal("momentum", 1.0),
        _make_signal("context", 1.0),
        _make_signal("risk", 1.0),
    ]
    assert aggregate(signals) == pytest.approx(1.0, abs=0.01)


def test_aggregate_all_agents_zero():
    signals = [
        _make_signal("technical", 0.0),
        _make_signal("momentum", 0.0),
        _make_signal("context", 0.0),
        _make_signal("risk", 0.0),
    ]
    assert aggregate(signals) == pytest.approx(0.0, abs=0.01)


def test_aggregate_weighted_correctly():
    signals = [
        _make_signal("technical", 1.0),
        _make_signal("momentum", 0.0),
        _make_signal("context", 0.0),
        _make_signal("risk", 0.0),
    ]
    expected = AGENT_WEIGHTS["technical"]
    assert aggregate(signals) == pytest.approx(expected, abs=0.01)


def test_aggregate_mixed_scores():
    signals = [
        _make_signal("technical", 0.8),
        _make_signal("momentum", 0.6),
        _make_signal("context", 0.9),
        _make_signal("risk", 0.5),
    ]
    expected = (0.8 * 0.35 + 0.6 * 0.25 + 0.9 * 0.20 + 0.5 * 0.20)
    assert aggregate(signals) == pytest.approx(expected, abs=0.01)


def test_aggregate_clamps_above_one():
    signals = [_make_signal("technical", 1.5)]
    result = aggregate(signals)
    assert result <= 1.0


def test_aggregate_clamps_below_zero():
    signals = [_make_signal("technical", -0.5)]
    result = aggregate(signals)
    assert result >= 0.0


def test_aggregate_unknown_agent_ignored():
    signals = [_make_signal("unknown_agent", 0.9)]
    assert aggregate(signals) == 0.0


def test_aggregate_custom_weights():
    signals = [
        _make_signal("technical", 1.0),
        _make_signal("momentum", 0.0),
    ]
    custom = {"technical": 0.5, "momentum": 0.5}
    assert aggregate(signals, weights=custom) == pytest.approx(0.5, abs=0.01)
