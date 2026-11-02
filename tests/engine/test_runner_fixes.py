"""Regression tests for the engine fixes (Nov 2026).

- Filters never block exits (SELL), only entries (BUY).
- Indicators are computed with the params written in the strategy.
- Partial take-profit levels sell only part of the position.
- The DB row created at entry is updated at exit (no ghost OPEN rows).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from core.indicators.registry import get_registry
from core.models import Candle, Position, Signal, SignalType, StrategyConfig
from core.risk.sizing import SymbolInfo
from core.strategy.loader import StrategyLoader, state_key
from engine.runner import TradingRunner

# Reuse the mocked-dependency fixtures of the main runner test module.
from tests.engine.test_runner import (  # noqa: F401
    config,
    mock_cache,
    mock_exchange_rest,
    mock_exchange_ws,
    mock_notifier,
    mock_repository,
    runner,
)

T0 = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _discover_indicators() -> None:
    # TradingRunner.start() normally does this.
    get_registry().discover()


def _candle(close: float, minute: int = 5, timeframe: str = "1m") -> Candle:
    return Candle(
        timestamp=T0.replace(minute=minute), open=close, high=close, low=close,
        close=close, volume=1.0, pair="BTCUSDT", timeframe=timeframe, is_closed=True,
    )


def _position(**overrides) -> Position:
    data = dict(
        pair="BTCUSDT", side="BUY", entry_price=100.0, quantity=1.0,
        entry_time=T0, stop_loss=98.0,
        take_profit_levels=[
            {"price": 102.0, "pct_to_close": 50.0, "hit": False},
            {"price": 104.0, "pct_to_close": 100.0, "hit": False},
        ],
        metadata={"strategy_name": "t", "trade_id": "row-1"},
    )
    data.update(overrides)
    return Position(**data)


# ----------------------------------------------------------------------
# Filters only apply to entries
# ----------------------------------------------------------------------

class TestFiltersOnlyOnEntries:
    def _setup(self, runner: TradingRunner, ema_value: float) -> None:
        runner._running = True
        runner._strategy_config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["BTCUSDT"], "timeframe": "5m",
            "entry_conditions": [{"indicator": "rsi", "operator": "below", "value": 30}],
            "exit_conditions": [{"indicator": "rsi", "operator": "above", "value": 70}],
            "filters": {"ema_trend": {"enabled": True, "ema_period": 50}},
            "risk": {"stop_loss_pct": 1.5},
            "indicators_needed": ["rsi"],
        })
        # Bypass indicator computation: inject states directly.
        runner._update_indicators = lambda pair, candle: runner._indicator_states[pair]  # type: ignore[method-assign]
        runner._indicator_states["BTCUSDT"] = {
            state_key("ema", {"period": 50}): {"ema": [ema_value]},
        }
        runner._execute_signal = AsyncMock()  # type: ignore[method-assign]

    @pytest.mark.asyncio
    async def test_buy_below_ema_is_rejected(self, runner: TradingRunner) -> None:
        self._setup(runner, ema_value=110.0)
        runner._indicator_states["BTCUSDT"]["rsi"] = {"current_rsi": 20.0, "prev_rsi": 25.0}
        await runner._process_strategy_candle("BTCUSDT", _candle(100.0, timeframe="5m"))
        runner._execute_signal.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sell_below_ema_goes_through(self, runner: TradingRunner) -> None:
        self._setup(runner, ema_value=110.0)
        runner._open_positions["BTCUSDT"] = _position()
        runner._indicator_states["BTCUSDT"]["rsi"] = {"current_rsi": 80.0, "prev_rsi": 75.0}
        await runner._process_strategy_candle("BTCUSDT", _candle(100.0, timeframe="5m"))
        runner._execute_signal.assert_awaited_once()
        assert runner._execute_signal.await_args.args[0].type == SignalType.SELL

    @pytest.mark.asyncio
    async def test_ema_filter_uses_its_own_period(self, runner: TradingRunner) -> None:
        """The EMA-20 default state must not be used when ema_period is 50."""
        self._setup(runner, ema_value=90.0)  # EMA 50 below price -> pass
        runner._indicator_states["BTCUSDT"]["ema"] = {"ema": [120.0]}  # EMA 20 above
        runner._indicator_states["BTCUSDT"]["rsi"] = {"current_rsi": 20.0, "prev_rsi": 25.0}
        await runner._process_strategy_candle("BTCUSDT", _candle(100.0, timeframe="5m"))
        runner._execute_signal.assert_awaited_once()


# ----------------------------------------------------------------------
# Params-aware indicator states
# ----------------------------------------------------------------------

class TestIndicatorParams:
    def test_warmup_and_update_use_condition_params(self, runner: TradingRunner) -> None:
        runner._strategy_config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["BTCUSDT"], "timeframe": "5m",
            "entry_conditions": [
                {"indicator": "ema", "params": {"period": 3}, "operator": "price_above"},
            ],
            "indicators_needed": ["ema"],
        })
        history = [_candle(100.0 + i, minute=i % 60, timeframe="5m") for i in range(30)]
        runner._warm_up_indicators("BTCUSDT", history)
        states = runner._indicator_states["BTCUSDT"]
        fast_key = state_key("ema", {"period": 3})
        assert fast_key in states and "ema" in states
        assert states[fast_key]["ema"][-1] != pytest.approx(states["ema"]["ema"][-1])

        runner._update_indicators("BTCUSDT", _candle(200.0, timeframe="5m"))
        assert len(states[fast_key]["ema"]) == 31


# ----------------------------------------------------------------------
# Partial take-profit
# ----------------------------------------------------------------------

class TestPartialTakeProfit:
    @pytest.mark.asyncio
    async def test_first_level_sells_half(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        runner._balance = 0.0
        runner._open_positions["BTCUSDT"] = _position()

        await runner._check_exits("BTCUSDT", _candle(102.5))

        position = runner._open_positions["BTCUSDT"]
        assert position.is_open
        assert position.quantity == pytest.approx(0.5)
        assert len(runner._daily_trades) == 1
        assert runner._daily_trades[0].quantity == pytest.approx(0.5)
        exit_fee = 0.5 * 102.5 * 0.001  # simulated 0.1 % fee
        assert runner._daily_trades[0].pnl_usdt == pytest.approx(1.25 - exit_fee)
        assert runner._balance == pytest.approx(51.25 - exit_fee)  # dry-run proceeds
        mock_repository.save_trade.assert_awaited_once()
        mock_repository.update_trade.assert_awaited_once_with("row-1", quantity=pytest.approx(0.5))

    @pytest.mark.asyncio
    async def test_second_level_closes_the_rest(self, runner: TradingRunner) -> None:
        runner._open_positions["BTCUSDT"] = _position()
        await runner._check_exits("BTCUSDT", _candle(102.5, minute=5))
        await runner._check_exits("BTCUSDT", _candle(104.5, minute=6))
        assert "BTCUSDT" not in runner._open_positions
        assert [t.quantity for t in runner._daily_trades] == pytest.approx([0.5, 0.5])

    @pytest.mark.asyncio
    async def test_tiny_remainder_closes_everything(self, runner: TradingRunner) -> None:
        runner._symbol_info["BTCUSDT"] = SymbolInfo(
            min_qty=0.001, step_size=0.001, min_notional=100.0, tick_size=0.01,
        )
        runner._open_positions["BTCUSDT"] = _position()  # 0.5 * 102.5 < 100 notional
        await runner._check_exits("BTCUSDT", _candle(102.5))
        assert "BTCUSDT" not in runner._open_positions

    @pytest.mark.asyncio
    async def test_live_partial_rearms_stop_loss(
        self, runner: TradingRunner, mock_exchange_rest: AsyncMock,
    ) -> None:
        runner._config.dry_run = False
        mock_exchange_rest.place_order = AsyncMock(return_value={
            "orderId": 1, "fills": [{"price": "102.4", "qty": "0.5"}],
        })
        mock_exchange_rest.set_stop_loss = AsyncMock(return_value={"orderId": 99})
        runner._open_positions["BTCUSDT"] = _position(
            metadata={"strategy_name": "t", "trade_id": "row-1", "sl_order_id": "42"},
        )

        await runner._check_exits("BTCUSDT", _candle(102.5))

        mock_exchange_rest.cancel_order.assert_awaited_once_with("BTCUSDT", "42")
        assert mock_exchange_rest.place_order.await_args.kwargs["quantity"] == pytest.approx(0.5)
        assert mock_exchange_rest.set_stop_loss.await_args.kwargs["quantity"] == pytest.approx(0.5)
        position = runner._open_positions["BTCUSDT"]
        assert position.metadata["sl_order_id"] == "99"
        assert runner._daily_trades[0].exit_price == pytest.approx(102.4)
        assert "BTCUSDT" not in runner._pending_close

    @pytest.mark.asyncio
    async def test_live_partial_failure_keeps_full_stop_loss(
        self, runner: TradingRunner, mock_exchange_rest: AsyncMock,
    ) -> None:
        runner._config.dry_run = False
        mock_exchange_rest.place_order = AsyncMock(side_effect=RuntimeError("boom"))
        runner._open_positions["BTCUSDT"] = _position(
            metadata={"strategy_name": "t", "sl_order_id": "42"},
        )

        await runner._check_exits("BTCUSDT", _candle(102.5))

        position = runner._open_positions["BTCUSDT"]
        assert position.quantity == pytest.approx(1.0)
        assert mock_exchange_rest.set_stop_loss.await_args.kwargs["quantity"] == pytest.approx(1.0)
        assert runner._daily_trades == []


# ----------------------------------------------------------------------
# DB rows
# ----------------------------------------------------------------------

class TestTradeRows:
    @pytest.mark.asyncio
    async def test_open_stores_row_id(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        mock_repository.save_trade = AsyncMock(return_value="row-7")
        runner._strategy_config = StrategyConfig(
            name="t", pairs=["BTCUSDT"], timeframe="5m", risk={"stop_loss_pct": 1.5},
        )
        runner._balance = 1000.0
        signal = Signal(type=SignalType.BUY, pair="BTCUSDT", timeframe="5m",
                        price=100.0, timestamp=T0, strategy_name="t")
        await runner._execute_signal(signal, "BTCUSDT", _candle(100.0, timeframe="5m"))
        assert runner._open_positions["BTCUSDT"].metadata["trade_id"] == "row-7"

    @pytest.mark.asyncio
    async def test_close_updates_open_row(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        runner._open_positions["BTCUSDT"] = _position(take_profit_levels=[])
        await runner._close_position(runner._open_positions["BTCUSDT"], _candle(97.0), "STOP_LOSS")
        mock_repository.save_trade.assert_not_awaited()
        kwargs = mock_repository.update_trade.await_args.kwargs
        assert mock_repository.update_trade.await_args.args == ("row-1",)
        assert kwargs["status"] == "CLOSED"
        assert kwargs["exit_price"] == pytest.approx(97.0)
        assert kwargs["exit_time"].tzinfo is None

    @pytest.mark.asyncio
    async def test_close_without_row_id_inserts(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        runner._open_positions["BTCUSDT"] = _position(take_profit_levels=[], metadata={})
        await runner._close_position(runner._open_positions["BTCUSDT"], _candle(97.0), "STOP_LOSS")
        mock_repository.save_trade.assert_awaited_once()
        mock_repository.update_trade.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_inserts_when_row_missing(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        mock_repository.update_trade = AsyncMock(return_value=None)
        runner._open_positions["BTCUSDT"] = _position(take_profit_levels=[])
        await runner._close_position(runner._open_positions["BTCUSDT"], _candle(97.0), "STOP_LOSS")
        mock_repository.save_trade.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_restore_keeps_row_id(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        mock_repository.get_trades = AsyncMock(return_value=[{
            "id": "row-9", "pair": "BTCUSDT", "side": "BUY", "entry_price": 100.0,
            "quantity": 0.5, "entry_time": "2026-02-10T12:00:00",
            "metadata_json": '{"stop_loss": 98.0}',
        }])
        await runner._restore_open_positions()
        assert runner._open_positions["BTCUSDT"].metadata["trade_id"] == "row-9"


# ----------------------------------------------------------------------
# Daily counters & circuit breaker
# ----------------------------------------------------------------------

def _losing_trade() -> "Trade":
    from core.models import Trade
    return Trade(pair="BTCUSDT", side="BUY", entry_price=100.0, exit_price=99.0,
                 quantity=1.0, pnl_usdt=-1.0)


class TestDailyRollover:
    @pytest.mark.asyncio
    async def test_counters_reset_on_new_utc_day(self, runner: TradingRunner, mock_repository: AsyncMock) -> None:
        await runner._roll_daily_stats(datetime(2026, 2, 10, 23, 59, tzinfo=timezone.utc))
        runner._daily_trade_count = 20
        runner._daily_pnl_usdt = -80.0
        runner._daily_trades = [_losing_trade()] * 3

        await runner._roll_daily_stats(datetime(2026, 2, 10, 23, 59, 30, tzinfo=timezone.utc))
        assert runner._daily_trade_count == 20  # same day: unchanged

        await runner._roll_daily_stats(datetime(2026, 2, 11, 0, 0, tzinfo=timezone.utc))
        assert runner._daily_trade_count == 0
        assert runner._daily_pnl_usdt == 0.0
        assert runner._daily_trades == []
        saved = mock_repository.save_daily_stats.await_args.args[0]
        assert str(saved["date"]) == "2026-02-10"  # stats of the finished day

    @pytest.mark.asyncio
    async def test_naive_timestamps_are_utc(self, runner: TradingRunner) -> None:
        await runner._roll_daily_stats(datetime(2026, 2, 10, 23, 0))
        runner._daily_trade_count = 5
        await runner._roll_daily_stats(datetime(2026, 2, 11, 0, 1))
        assert runner._daily_trade_count == 0


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_breaker_uses_candle_time_and_does_not_retrip(self, runner: TradingRunner) -> None:
        runner._running = True
        runner._strategy_config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["BTCUSDT"], "timeframe": "5m",
            "entry_conditions": [{"indicator": "rsi", "operator": "below", "value": 30}],
            "risk": {"stop_loss_pct": 1.5}, "indicators_needed": ["rsi"],
        })
        runner._update_indicators = lambda pair, candle: {  # type: ignore[method-assign]
            "rsi": {"current_rsi": 20.0, "prev_rsi": 25.0}}
        runner._execute_signal = AsyncMock()  # type: ignore[method-assign]
        runner._balance = 1000.0
        runner._daily_trades = [_losing_trade()] * 3

        t = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)
        candle = lambda ts: Candle(timestamp=ts, open=100, high=100, low=100, close=100,  # noqa: E731
                                   volume=1, pair="BTCUSDT", timeframe="5m")

        await runner._process_strategy_candle("BTCUSDT", candle(t))
        assert runner._circuit_breaker_active
        assert runner._circuit_breaker_until == t + timedelta(minutes=30)
        runner._execute_signal.assert_not_awaited()

        await runner._process_strategy_candle("BTCUSDT", candle(t + timedelta(minutes=10)))
        runner._execute_signal.assert_not_awaited()  # still paused

        # After the pause the same 3 old losses must not re-trip the breaker.
        await runner._process_strategy_candle("BTCUSDT", candle(t + timedelta(minutes=31)))
        assert not runner._circuit_breaker_active
        runner._execute_signal.assert_awaited_once()


class TestDryRunAccounting:
    @pytest.mark.asyncio
    async def test_round_trip_debits_cost_and_fees(self, runner: TradingRunner) -> None:
        runner._strategy_config = StrategyConfig(
            name="t", pairs=["BTCUSDT"], timeframe="5m",
            risk={"stop_loss_pct": 1.5, "max_position_size_pct": 10.0},
        )
        runner._balance = 1000.0
        signal = Signal(type=SignalType.BUY, pair="BTCUSDT", timeframe="5m",
                        price=100.0, timestamp=T0, strategy_name="t")
        await runner._execute_signal(signal, "BTCUSDT", _candle(100.0, timeframe="5m"))

        position = runner._open_positions["BTCUSDT"]
        cost = position.quantity * 100.0
        assert cost == pytest.approx(100.0)  # capped at 10 % of the balance
        assert runner._balance == pytest.approx(1000.0 - cost * 1.001)

        await runner._close_position(position, _candle(100.0), "STRATEGY_EXIT")
        trade = runner._daily_trades[0]
        assert trade.fees == pytest.approx(0.2)  # 0.1 % in + 0.1 % out
        assert trade.pnl_usdt == pytest.approx(-0.2)
        assert runner._balance == pytest.approx(1000.0 - 0.2)

    @pytest.mark.asyncio
    async def test_fee_can_be_disabled(self, runner: TradingRunner) -> None:
        runner._config.dry_run_fee_pct = 0.0
        runner._open_positions["BTCUSDT"] = _position(take_profit_levels=[], metadata={})
        await runner._close_position(runner._open_positions["BTCUSDT"], _candle(101.0), "STRATEGY_EXIT")
        assert runner._daily_trades[0].fees == 0.0
        assert runner._daily_trades[0].pnl_usdt == pytest.approx(1.0)


# ----------------------------------------------------------------------
# Multi-timeframe conditions
# ----------------------------------------------------------------------

MTF_STRATEGY = {
    "name": "HA MTF", "pairs": ["BTCUSDT"], "timeframe": "5m",
    "entry_conditions": [
        {"indicator": "heikin_ashi", "params": {"timeframe": "15m"}, "operator": "is_green"},
        {"indicator": "heikin_ashi", "operator": "flip_to_green"},
    ],
    "exit_conditions": [{"indicator": "heikin_ashi", "operator": "flip_to_red"}],
    "risk": {"stop_loss_pct": 2.0},
}


def _minute_candle(i: int, close: float) -> Candle:
    return Candle(
        timestamp=T0 + timedelta(minutes=i), open=close, high=close + 0.5,
        low=close - 0.5, close=close, volume=1.0, pair="BTCUSDT",
        timeframe="1m", is_closed=True,
    )


class TestMultiTimeframe:
    def _load(self, runner: TradingRunner) -> None:
        runner._running = True
        runner._strategy_config = StrategyLoader().load_from_dict(dict(MTF_STRATEGY))
        runner._setup_timeframe_aggregator()

    def test_loader_lists_timeframes_strategy_last(self) -> None:
        config = StrategyLoader().load_from_dict(dict(MTF_STRATEGY))
        assert StrategyLoader().timeframes(config) == ["15m", "5m"]
        specs = StrategyLoader().indicator_specs(config)
        assert specs["heikin_ashi@15m"] == ("heikin_ashi", {}, "15m")
        assert specs["heikin_ashi"] == ("heikin_ashi", {}, None)

    def test_aggregator_builds_every_timeframe(self, runner: TradingRunner) -> None:
        self._load(runner)
        assert runner._effective_strategy_tf == "5m"
        assert runner._timeframe_aggregator.target_timeframes == ["15m", "5m"]

    def test_warmup_only_fills_states_of_that_timeframe(self, runner: TradingRunner) -> None:
        self._load(runner)
        hist_15m = [
            Candle(timestamp=T0 - timedelta(minutes=15 * (30 - i)), open=100, high=101,
                   low=99, close=100 + i, volume=1, pair="BTCUSDT", timeframe="15m")
            for i in range(30)
        ]
        runner._warm_up_indicators("BTCUSDT", hist_15m, "15m")
        states = runner._indicator_states["BTCUSDT"]
        assert "heikin_ashi@15m" in states
        assert "heikin_ashi" not in states

    @pytest.mark.asyncio
    async def test_higher_tf_state_follows_15m_candles(self, runner: TradingRunner) -> None:
        self._load(runner)
        runner._execute_signal = AsyncMock()  # type: ignore[method-assign]
        evaluated: list[str] = []
        original = runner._process_strategy_candle

        async def spy(pair: str, candle: Candle) -> None:
            evaluated.append(candle.timeframe)
            await original(pair, candle)

        runner._process_strategy_candle = spy  # type: ignore[method-assign]
        for i in range(60):
            await runner.on_candle({
                "pair": "BTCUSDT", "timeframe": "1m",
                "timestamp": (T0 + timedelta(minutes=i)).isoformat(),
                "open": 100 + i, "high": 101 + i, "low": 99 + i, "close": 100.5 + i,
                "volume": 1.0, "is_closed": True,
            })
        states = runner._indicator_states["BTCUSDT"]
        # 60 one-minute candles -> 4 closed 15m candles, 12 closed 5m candles
        # (the last bucket closes on the next candle).
        assert len(states["heikin_ashi@15m"]["is_green"]) in (3, 4)
        assert len(states["heikin_ashi"]["is_green"]) in (11, 12)
        assert set(evaluated) == {"5m"}


# ----------------------------------------------------------------------
# Time-based exit (risk.max_hold_minutes)
# ----------------------------------------------------------------------

class TestMaxHoldMinutes:
    @pytest.mark.asyncio
    async def test_position_closes_after_max_hold(self, runner: TradingRunner) -> None:
        runner._running = True
        runner._strategy_config = StrategyLoader().load_from_dict({
            "name": "t", "pairs": ["BTCUSDT"], "timeframe": "1m",
            "entry_conditions": [{"indicator": "rsi", "operator": "above", "value": 0}],
            "risk": {"stop_loss_pct": 5.0, "max_hold_minutes": 30,
                     "trailing_activation_pct": 0.0, "trailing_distance_pct": 0.0},
        })
        signal = Signal(type=SignalType.BUY, pair="BTCUSDT", price=100.0,
                        timestamp=T0, reason="test", strategy_name="t", timeframe="1m")
        await runner._execute_signal(signal, "BTCUSDT", _candle(100.0, minute=0))
        position = runner._open_positions["BTCUSDT"]
        assert position.metadata["max_hold_minutes"] == 30

        await runner._check_exits("BTCUSDT", _candle(100.0, minute=29))
        assert "BTCUSDT" in runner._open_positions
        await runner._check_exits("BTCUSDT", _candle(100.0, minute=30))
        assert "BTCUSDT" not in runner._open_positions
        assert runner._daily_trades[-1].exit_reason.startswith("TIME_EXIT")
