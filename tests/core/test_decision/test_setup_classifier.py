"""Tests for core.decision.setup_classifier."""

from core.decision.setup_classifier import (
    classify_setup,
    SETUP_BREAKOUT,
    SETUP_PULLBACK,
    SETUP_MEAN_REVERSION,
    SETUP_CONSOLIDATION_EXIT,
    SETUP_TREND_FOLLOWING,
    SETUP_UNKNOWN,
)


def test_classify_empty_states():
    assert classify_setup({}) == SETUP_UNKNOWN


def test_classify_no_price():
    assert classify_setup({"ema_9": 100}) == SETUP_UNKNOWN


def test_classify_breakout():
    states = {
        "price": 105.0,
        "ema_9": 104.0,
        "ema_21": 103.0,
        "ema_50": 102.0,
        "ema_200": 100.0,
        "rsi_14": 65.0,
        "volume_ratio": 2.0,
        "macd_histogram": 0.5,
        "higher_highs": True,
        "higher_lows": True,
    }
    assert classify_setup(states) == SETUP_BREAKOUT


def test_classify_pullback():
    states = {
        "price": 103.0,
        "ema_9": 104.0,
        "ema_21": 103.2,
        "ema_50": 102.0,
        "ema_200": 100.0,
        "rsi_14": 40.0,
        "volume_ratio": 0.8,
        "macd_histogram": -0.1,
        "higher_highs": True,
        "higher_lows": True,
    }
    assert classify_setup(states) == SETUP_PULLBACK


def test_classify_mean_reversion():
    states = {
        "price": 95.0,
        "ema_9": 98.0,
        "ema_21": 99.0,
        "ema_50": 100.0,
        "rsi_14": 25.0,
        "volume_ratio": 1.5,
        "bollinger_lower": 95.5,
        "bollinger_upper": 105.0,
        "higher_highs": False,
        "higher_lows": False,
    }
    assert classify_setup(states) == SETUP_MEAN_REVERSION


def test_classify_consolidation_exit():
    states = {
        "price": 101.0,
        "ema_9": 100.0,
        "ema_21": 99.5,
        "ema_50": 99.0,
        "rsi_14": 55.0,
        "volume_ratio": 2.5,
        "bollinger_lower": 99.5,
        "bollinger_upper": 100.5,
        "macd_histogram": 0.1,
        "higher_highs": True,
        "higher_lows": True,
    }
    assert classify_setup(states) == SETUP_CONSOLIDATION_EXIT


def test_classify_trend_following():
    states = {
        "price": 105.0,
        "ema_9": 104.0,
        "ema_21": 103.0,
        "ema_50": 102.0,
        "ema_200": 100.0,
        "rsi_14": 60.0,
        "volume_ratio": 1.0,
        "macd_histogram": 0.1,
        "higher_highs": True,
        "higher_lows": True,
    }
    assert classify_setup(states) == SETUP_TREND_FOLLOWING


def test_classify_unknown_no_clear_setup():
    states = {
        "price": 100.0,
        "ema_9": 99.0,
        "ema_21": 101.0,
        "ema_50": 98.0,
        "rsi_14": 50.0,
        "volume_ratio": 1.0,
        "higher_highs": False,
        "higher_lows": True,
    }
    assert classify_setup(states) == SETUP_UNKNOWN
