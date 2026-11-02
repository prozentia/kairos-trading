"""Regression tests for the strategy-engine fixes (Nov 2026).

- Condition params are honoured (one indicator state per params set).
- List-format filters are normalised to the dict format read by check_all.
- Every seed template only uses operators supported by its indicators.
- Incremental update() with params stays consistent with calculate().
- msb_glissant.update() works on a state produced by calculate().
"""

from __future__ import annotations

import ast
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from core.indicators.registry import get_registry
from core.models import Candle, SignalType, StrategyConfig
from core.strategy.evaluator import StrategyEvaluator
from core.strategy.filters import SignalFilter
from core.strategy.loader import StrategyLoader, normalize_filters, state_key

SEED_FILE = Path(__file__).resolve().parents[3] / "scripts" / "seed_strategies.py"


@pytest.fixture(scope="module", autouse=True)
def _discover() -> None:
    get_registry().discover()


def _candles(n: int = 400, seed: int = 7) -> list[Candle]:
    """Deterministic random-walk candles with trend changes."""
    rng = random.Random(seed)
    price = 100.0
    start = datetime(2026, 1, 1)
    out = []
    for i in range(n):
        drift = 0.3 * math.sin(i / 25)
        o = price
        c = max(1.0, o + drift + rng.uniform(-1.0, 1.0))
        h = max(o, c) + rng.uniform(0, 0.6)
        lo = min(o, c) - rng.uniform(0, 0.6)
        out.append(Candle(
            timestamp=start + timedelta(minutes=5 * i), open=o, high=h, low=lo,
            close=c, volume=rng.uniform(5, 50) * (4 if i % 37 == 0 else 1),
            pair="TESTUSDT", timeframe="5m",
        ))
        price = c
    return out


def _seed_definitions() -> list[dict[str, Any]]:
    tree = ast.parse(SEED_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "STRATEGIES":
            return [s["definition"] for s in ast.literal_eval(node.value)]
    raise AssertionError("STRATEGIES not found in seed_strategies.py")


def _compute_states(config: StrategyConfig, candles: list[Candle]) -> dict[str, dict]:
    registry = get_registry()
    states = {}
    for key, spec in StrategyLoader().indicator_specs(config).items():
        states[key] = registry.get(spec.indicator).calculate(candles, **spec.params)
    return states


def _leaf_conditions(node: Any) -> list[dict]:
    if isinstance(node, list):
        return [c for child in node for c in _leaf_conditions(child)]
    if isinstance(node, dict):
        if "indicator" in node:
            return [node]
        return [c for child in node.get("conditions", []) for c in _leaf_conditions(child)]
    return []


# ----------------------------------------------------------------------
# state_key / specs
# ----------------------------------------------------------------------

class TestStateKey:
    def test_no_params_uses_bare_key(self) -> None:
        assert state_key("ema") == "ema"
        assert state_key("ema", {}) == "ema"

    def test_params_are_part_of_key(self) -> None:
        assert state_key("ema", {"period": 200}) != state_key("ema", {"period": 50})
        assert state_key("ema", {"period": 200}).startswith("ema|")

    def test_key_is_order_independent(self) -> None:
        assert state_key("macd", {"a": 1, "b": 2}) == state_key("macd", {"b": 2, "a": 1})

    def test_timeframe_param_gets_its_own_state(self) -> None:
        assert state_key("heikin_ashi", {"timeframe": "15m"}) == "heikin_ashi@15m"
        assert state_key("ema", {"timeframe": "15m", "period": 50}) == 'ema@15m|{"period": 50}'


class TestIndicatorSpecs:
    def test_specs_include_condition_params_and_filters(self) -> None:
        config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["BTCUSDT"], "timeframe": "15m",
            "entry_conditions": [
                {"indicator": "ema_cross", "params": {"fast_period": 5, "slow_period": 13},
                 "operator": "golden_cross"},
            ],
            "exit_conditions": [],
            "filters": [
                {"type": "ema_trend", "params": {"indicator": "ema", "period": 200,
                                                 "operator": "price_above"}, "enabled": True},
                {"type": "adx_trend", "params": {"indicator": "adx_dmi", "period": 10,
                                                 "min_value": 30}, "enabled": True},
            ],
            "indicators_needed": ["ema_cross"],
        })
        specs = StrategyLoader().indicator_specs(config)
        assert specs[state_key("ema_cross", {"fast_period": 5, "slow_period": 13})] == (
            "ema_cross", {"fast_period": 5, "slow_period": 13}, None)
        assert specs[state_key("ema", {"period": 200})] == ("ema", {"period": 200}, None)
        assert specs[state_key("adx_dmi", {"period": 10})] == ("adx_dmi", {"period": 10}, None)
        assert "ema_cross" in specs  # default state kept for indicators_needed

    def test_condition_params_change_indicator_values(self) -> None:
        config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["X"], "timeframe": "5m",
            "entry_conditions": [{"indicator": "rsi", "params": {"period": 3},
                                  "operator": "above", "value": 0}],
            "indicators_needed": ["rsi"],
        })
        states = _compute_states(config, _candles())
        fast = states[state_key("rsi", {"period": 3})]["current_rsi"]
        default = states["rsi"]["current_rsi"]
        assert fast != pytest.approx(default)

    def test_evaluator_reads_the_params_state(self) -> None:
        config = StrategyConfig(
            name="t", pairs=["X"], timeframe="5m",
            entry_conditions=[{"indicator": "rsi", "params": {"period": 3},
                               "operator": "below", "value": 50}],
            indicators_needed=["rsi"],
        )
        states = {
            "rsi": {"current_rsi": 80.0, "prev_rsi": 80.0},
            state_key("rsi", {"period": 3}): {"current_rsi": 20.0, "prev_rsi": 20.0},
        }
        signal = StrategyEvaluator().evaluate(config, states, {"pair": "X", "price": 1.0})
        assert signal.type == SignalType.BUY

    def test_evaluator_falls_back_to_bare_key(self) -> None:
        config = StrategyConfig(
            name="t", pairs=["X"], timeframe="5m",
            entry_conditions=[{"indicator": "rsi", "params": {"period": 3},
                               "operator": "below", "value": 50}],
            indicators_needed=["rsi"],
        )
        states = {"rsi": {"current_rsi": 20.0, "prev_rsi": 20.0}}
        signal = StrategyEvaluator().evaluate(config, states, {"pair": "X", "price": 1.0})
        assert signal.type == SignalType.BUY


# ----------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------

class TestFilterNormalisation:
    def test_list_format_is_converted(self) -> None:
        out = normalize_filters([
            {"type": "ema_trend", "params": {"indicator": "ema", "period": 50,
                                             "operator": "price_above"}, "enabled": True},
            {"type": "loss_cooldown", "params": {"cooldown_minutes": 9}, "enabled": False},
        ])
        assert out == {
            "ema_trend": {"enabled": True, "ema_period": 50},
            "loss_cooldown": {"enabled": False, "cooldown_minutes": 9},
        }

    def test_dict_format_is_unchanged(self) -> None:
        filters = {"ema_trend": {"enabled": True, "ema_period": 50}}
        assert normalize_filters(filters) is filters

    def test_empty(self) -> None:
        assert normalize_filters([]) == {}
        assert normalize_filters(None) == {}

    def test_loader_normalises_filters(self) -> None:
        config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["X"],
            "filters": [{"type": "ema_trend", "params": {"period": 20}, "enabled": True}],
        })
        assert config.filters == {"ema_trend": {"enabled": True, "ema_period": 20}}


class TestAdxTrendFilter:
    def _config(self) -> StrategyConfig:
        return StrategyConfig(name="t", filters={"adx_trend": {"enabled": True, "min_value": 25}})

    def test_rejects_weak_trend(self) -> None:
        ok, reason = SignalFilter().check_all(self._config(), {"adx_value": 18.0})
        assert not ok and "ADX" in reason

    def test_accepts_strong_trend(self) -> None:
        ok, _ = SignalFilter().check_all(self._config(), {"adx_value": 31.0})
        assert ok

    def test_rejects_when_adx_unknown(self) -> None:
        ok, _ = SignalFilter().check_all(self._config(), {})
        assert not ok


# ----------------------------------------------------------------------
# Seed templates
# ----------------------------------------------------------------------

SEEDS = _seed_definitions()


@pytest.mark.parametrize("definition", SEEDS, ids=[d["name"] for d in SEEDS])
def test_seed_operators_are_supported(definition: dict) -> None:
    """Every condition of every seed template must evaluate without error."""
    config = StrategyLoader().load_from_dict(dict(definition))
    assert StrategyLoader().validate(config) == []
    states = _compute_states(config, _candles())
    registry = get_registry()
    for cond in _leaf_conditions(config.entry_conditions) + _leaf_conditions(config.exit_conditions):
        state = states[state_key(cond["indicator"], cond.get("params"))]
        # Raises ValueError on an unknown operator.
        registry.get(cond["indicator"]).evaluate(state, cond["operator"], cond.get("value"))


@pytest.mark.parametrize("definition", SEEDS, ids=[d["name"] for d in SEEDS])
def test_seed_filters_are_dict_after_loading(definition: dict) -> None:
    config = StrategyLoader().load_from_dict(dict(definition))
    assert isinstance(config.filters, dict)


# ----------------------------------------------------------------------
# Incremental update consistency
# ----------------------------------------------------------------------

UPDATE_CASES = [
    ("ema", {"period": 50}, "ema"),
    ("rsi", {"period": 7}, "current_rsi"),
    ("ema_cross", {"fast_period": 5, "slow_period": 13}, "fast_ema"),
    ("adx_dmi", {"period": 10}, "adx"),
    ("donchian", {"period": 10}, "upper"),
    ("volume", {"ma_period": 10}, "vol_sma"),
    ("bollinger", {"period": 10, "std_dev": 2.0}, "lower"),
]


def _last(value: Any) -> Any:
    if isinstance(value, list):
        for v in reversed(value):
            if v is not None:
                return v
        return None
    return value


@pytest.mark.parametrize("key,params,field_name", UPDATE_CASES, ids=[c[0] for c in UPDATE_CASES])
def test_update_with_params_matches_calculate(key: str, params: dict, field_name: str) -> None:
    candles = _candles(300)
    indicator = get_registry().get(key)
    state = indicator.calculate(candles[:200], **params)
    for c in candles[200:]:
        state = indicator.update(c, state, **params)
    full = indicator.calculate(candles, **params)
    assert _last(state.get(field_name)) == pytest.approx(_last(full.get(field_name)), rel=1e-6)


def test_msb_glissant_update_after_calculate() -> None:
    """update() used to crash with IndexError on a calculate() state."""
    candles = _candles(300)
    indicator = get_registry().get("msb_glissant")
    state = indicator.calculate(candles[:200])
    for c in candles[200:]:
        state = indicator.update(c, state)
    assert len(state["_candle_highs"]) == len(state["prices"]) == 300
    full = indicator.calculate(candles)
    assert state["msb_high"] == full["msb_high"]
    assert state["msb_low"] == full["msb_low"]
