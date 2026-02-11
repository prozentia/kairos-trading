"""Tests for the indicator registry and auto-discovery mechanism."""

import pytest

from core.indicators.base import BaseIndicator
from core.indicators.registry import IndicatorRegistry, get_registry


# ---------------------------------------------------------------------------
# Fresh registry (isolated from global singleton)
# ---------------------------------------------------------------------------

class _DummyIndicator(BaseIndicator):
    """Minimal indicator for registry tests."""

    name = "Dummy"
    key = "dummy_test"
    category = "test"
    default_params = {"period": 10}

    def calculate(self, candles, **params):
        return {}

    def update(self, candle, state, **params):
        return state

    def evaluate(self, state, operator, value=None):
        return False


class _DummyTrend(BaseIndicator):
    name = "Dummy Trend"
    key = "dummy_trend"
    category = "trend"
    default_params = {}

    def calculate(self, candles, **params):
        return {}

    def update(self, candle, state, **params):
        return state

    def evaluate(self, state, operator, value=None):
        return False


class _DummyMomentum(BaseIndicator):
    name = "Dummy Momentum"
    key = "dummy_momentum"
    category = "momentum"
    default_params = {}

    def calculate(self, candles, **params):
        return {}

    def update(self, candle, state, **params):
        return state

    def evaluate(self, state, operator, value=None):
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_register_indicator():
    """Registering an indicator should make it retrievable."""
    reg = IndicatorRegistry()
    reg.register_class(_DummyIndicator)
    assert "dummy_test" in reg
    assert len(reg) == 1


def test_get_indicator():
    """get() should return the registered indicator instance."""
    reg = IndicatorRegistry()
    reg.register_class(_DummyIndicator)
    ind = reg.get("dummy_test")
    assert isinstance(ind, _DummyIndicator)
    assert ind.key == "dummy_test"
    assert ind.category == "test"


def test_get_nonexistent_indicator():
    """get() should raise KeyError for unknown indicator keys."""
    reg = IndicatorRegistry()
    with pytest.raises(KeyError, match="Unknown indicator"):
        reg.get("nonexistent_indicator_xyz")


def test_duplicate_registration_raises():
    """Registering the same key twice should raise ValueError."""
    reg = IndicatorRegistry()
    reg.register_class(_DummyIndicator)
    with pytest.raises(ValueError, match="Duplicate indicator key"):
        reg.register_class(_DummyIndicator)


def test_all_indicators_registered():
    """The global registry should contain all 23 indicator modules after discovery.

    Indicator modules: adx_dmi, atr, bollinger, cci, chaikin_money_flow,
    donchian, ema, ema_cross, heikin_ashi, ichimoku, keltner, macd,
    msb_glissant, parabolic_sar, roc, rsi, sma, stochastic,
    stochastic_rsi, supertrend, tsi, volume, vwap.
    """
    registry = get_registry()
    registry.discover()

    expected_keys = {
        "adx_dmi", "atr", "bollinger", "cci", "chaikin_money_flow",
        "donchian", "ema", "ema_cross", "heikin_ashi", "ichimoku",
        "keltner", "macd", "msb_glissant", "parabolic_sar", "roc",
        "rsi", "sma", "stochastic", "stochastic_rsi", "supertrend",
        "tsi", "volume", "vwap",
    }

    registered_keys = set(registry.keys())
    missing = expected_keys - registered_keys
    assert not missing, f"Missing indicators: {missing}"
    assert len(registry) >= 23, f"Expected >= 23 indicators, got {len(registry)}"


def test_by_category():
    """by_category() should correctly filter indicators."""
    reg = IndicatorRegistry()
    reg.register_class(_DummyTrend)
    reg.register_class(_DummyMomentum)
    reg.register_class(_DummyIndicator)

    trend = reg.by_category("trend")
    assert len(trend) == 1
    assert trend[0].key == "dummy_trend"

    momentum = reg.by_category("momentum")
    assert len(momentum) == 1
    assert momentum[0].key == "dummy_momentum"

    # Non-existent category returns empty list
    empty = reg.by_category("nonexistent")
    assert len(empty) == 0


def test_registry_keys_sorted():
    """keys() should return sorted list."""
    reg = IndicatorRegistry()
    reg.register_class(_DummyMomentum)
    reg.register_class(_DummyTrend)
    reg.register_class(_DummyIndicator)

    keys = reg.keys()
    assert keys == sorted(keys)


def test_registry_repr():
    """repr should show indicator count."""
    reg = IndicatorRegistry()
    assert "indicators=0" in repr(reg)
    reg.register_class(_DummyIndicator)
    assert "indicators=1" in repr(reg)
