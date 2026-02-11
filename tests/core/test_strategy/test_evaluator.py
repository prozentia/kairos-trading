"""Tests for the strategy condition evaluator.

The evaluator interprets the declarative JSON conditions from a
StrategyConfig and determines whether entry/exit signals should fire.
Tests are skipped until the evaluator module is implemented.
"""

from datetime import datetime, timezone

import pytest

from core.models import Candle, Signal, SignalType, StrategyConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candle(close: float = 97_500.0) -> Candle:
    """Create a minimal candle for testing."""
    return Candle(
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        open=close - 50,
        high=close + 100,
        low=close - 100,
        close=close,
        volume=5.0,
        pair="BTC/USDT",
        timeframe="1m",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Strategy evaluator not implemented yet")
def test_simple_and_condition():
    """AND logic: all conditions must be True for a BUY signal."""
    # Scenario: RSI < 30 AND price < lower BB
    config = StrategyConfig(
        name="test_and",
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {"indicator": "rsi", "operator": "below", "value": 30},
                {"indicator": "bollinger", "operator": "touch_lower"},
            ],
        },
    )
    # When both conditions are satisfied
    indicator_states = {
        "rsi": {"current_rsi": 25.0},
        "bollinger": {"touch_lower": True},
    }
    # TODO: evaluator.evaluate_entry(config, indicator_states, candle)
    # assert signal.type == SignalType.BUY


@pytest.mark.skip(reason="Strategy evaluator not implemented yet")
def test_simple_or_condition():
    """OR logic: any condition being True should generate a signal."""
    config = StrategyConfig(
        name="test_or",
        exit_conditions={
            "logic": "OR",
            "conditions": [
                {"indicator": "heikin_ashi", "operator": "is_red"},
                {"indicator": "rsi", "operator": "above", "value": 70},
            ],
        },
    )
    # Only one condition satisfied
    indicator_states = {
        "heikin_ashi": {"is_red": False, "is_green": True},
        "rsi": {"current_rsi": 75.0},
    }
    # TODO: evaluator.evaluate_exit(config, indicator_states, candle)
    # assert signal.type == SignalType.SELL


@pytest.mark.skip(reason="Strategy evaluator not implemented yet")
def test_nested_conditions():
    """Nested conditions: AND containing OR sub-groups."""
    config = StrategyConfig(
        name="test_nested",
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {"indicator": "heikin_ashi", "operator": "is_green"},
                {
                    "logic": "OR",
                    "conditions": [
                        {"indicator": "rsi", "operator": "below", "value": 30},
                        {"indicator": "bollinger", "operator": "touch_lower"},
                    ],
                },
            ],
        },
    )
    # HA is green AND (RSI < 30 OR BB touch_lower)
    # -> HA green + BB touch but RSI at 50 => should still trigger
    indicator_states = {
        "heikin_ashi": {"is_green": True},
        "rsi": {"current_rsi": 50.0},
        "bollinger": {"touch_lower": True},
    }
    # TODO: evaluate and assert signal type


@pytest.mark.skip(reason="Strategy evaluator not implemented yet")
def test_not_condition():
    """NOT logic: inverts a condition result."""
    config = StrategyConfig(
        name="test_not",
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {"indicator": "heikin_ashi", "operator": "is_green"},
                {
                    "logic": "NOT",
                    "condition": {"indicator": "rsi", "operator": "above", "value": 70},
                },
            ],
        },
    )
    # HA is green AND NOT(RSI > 70) => should fire when RSI is low
    indicator_states = {
        "heikin_ashi": {"is_green": True},
        "rsi": {"current_rsi": 45.0},
    }
    # TODO: evaluate and assert BUY signal


@pytest.mark.skip(reason="Strategy evaluator not implemented yet")
def test_no_signal_when_conditions_not_met():
    """When entry conditions are not met, signal should be NO_SIGNAL."""
    config = StrategyConfig(
        name="test_no_signal",
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {"indicator": "rsi", "operator": "below", "value": 30},
                {"indicator": "bollinger", "operator": "touch_lower"},
            ],
        },
    )
    # RSI is 50 (not below 30) -> should NOT generate a signal
    indicator_states = {
        "rsi": {"current_rsi": 50.0},
        "bollinger": {"touch_lower": False},
    }
    # TODO: evaluator should return NO_SIGNAL
