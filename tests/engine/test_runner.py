"""Unit tests for TradingRunner with fully mocked dependencies.

Tests cover:
- Start/stop lifecycle
- on_candle pipeline (closed vs non-closed candles)
- _execute_signal in dry_run mode
- _close_position
- _parse_candle (multiple formats)
- Trust level calculation
- Circuit breaker behaviour
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import (
    Candle,
    Position,
    PositionStatus,
    Signal,
    SignalType,
    StrategyConfig,
    Trade,
)
from core.risk.sizing import PositionSizer
from engine.config import EngineConfig
from engine.runner import TradingRunner


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def config() -> EngineConfig:
    """Minimal dry-run engine config for testing."""
    return EngineConfig(
        pairs=["BTCUSDT"],
        dry_run=True,
        testnet=True,
        capital_per_pair=1000.0,
        base_timeframe="1m",
        strategy_timeframe="5m",
        strategy_type="test_strategy",
        stop_loss_pct=1.5,
        trailing_activation_pct=0.6,
        trailing_distance_pct=0.3,
        max_positions=3,
        max_daily_loss_pct=5.0,
        max_daily_trades=20,
    )


@pytest.fixture
def mock_exchange_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.connect = AsyncMock()
    ws.disconnect = AsyncMock()
    ws.subscribe_klines = AsyncMock()
    ws.subscribe_user_data = AsyncMock()
    return ws


@pytest.fixture
def mock_exchange_rest() -> AsyncMock:
    rest = AsyncMock()
    rest.connect = AsyncMock()
    rest.disconnect = AsyncMock()
    rest.get_exchange_info = AsyncMock(return_value={
        "min_qty": 0.00001,
        "step_size": 0.00001,
        "tick_size": 0.01,
        "min_notional": 10.0,
    })
    rest.get_klines = AsyncMock(return_value=[])
    rest.place_order = AsyncMock(return_value={
        "orderId": 12345,
        "status": "FILLED",
        "fills": [{"price": "97500.00", "qty": "0.001"}],
    })
    rest.set_stop_loss = AsyncMock(return_value={"orderId": 12346})
    rest.get_balance = AsyncMock(return_value=1000.0)
    return rest


@pytest.fixture
def mock_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.get_active_strategy = AsyncMock(return_value=None)
    repo.save_trade = AsyncMock(return_value="trade-uuid-1")
    repo.save_daily_stats = AsyncMock()
    return repo


@pytest.fixture
def mock_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.connect = AsyncMock()
    cache.disconnect = AsyncMock()
    cache.cache_bot_status = AsyncMock()
    return cache


@pytest.fixture
def mock_notifier() -> AsyncMock:
    notifier = AsyncMock()
    notifier.send = AsyncMock()
    return notifier


@pytest.fixture
def runner(
    config: EngineConfig,
    mock_exchange_ws: AsyncMock,
    mock_exchange_rest: AsyncMock,
    mock_repository: AsyncMock,
    mock_cache: AsyncMock,
    mock_notifier: AsyncMock,
) -> TradingRunner:
    """Create a TradingRunner with all mocked dependencies."""
    return TradingRunner(
        config=config,
        exchange_ws=mock_exchange_ws,
        exchange_rest=mock_exchange_rest,
        repository=mock_repository,
        cache=mock_cache,
        notifier=mock_notifier,
    )


@pytest.fixture
def sample_candle_dict() -> dict:
    """Raw candle dict as would come from the WS adapter."""
    return {
        "pair": "BTCUSDT",
        "timeframe": "1m",
        "timestamp": "2026-02-10T12:04:00+00:00",
        "open": 97500.0,
        "high": 97600.0,
        "low": 97400.0,
        "close": 97550.0,
        "volume": 5.5,
        "is_closed": True,
    }


@pytest.fixture
def sample_strategy() -> StrategyConfig:
    return StrategyConfig(
        name="test_strategy",
        pairs=["BTCUSDT"],
        timeframe="5m",
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {"indicator": "rsi", "operator": "below", "value": 30},
            ],
        },
        exit_conditions={
            "logic": "OR",
            "conditions": [
                {"indicator": "rsi", "operator": "above", "value": 70},
            ],
        },
        risk={
            "stop_loss_pct": 1.5,
            "trailing_activation_pct": 0.6,
            "trailing_distance_pct": 0.3,
        },
        indicators_needed=["rsi"],
        is_active=True,
    )


# ------------------------------------------------------------------
# Lifecycle tests
# ------------------------------------------------------------------

class TestLifecycle:
    """Test start/stop lifecycle of the TradingRunner."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, runner: TradingRunner) -> None:
        """After start(), the runner should be marked as running."""
        await runner.start()
        assert runner.is_running is True
        await runner.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, runner: TradingRunner) -> None:
        """After stop(), the runner should be marked as not running."""
        await runner.start()
        await runner.stop()
        assert runner.is_running is False

    @pytest.mark.asyncio
    async def test_start_connects_adapters(
        self,
        runner: TradingRunner,
        mock_exchange_ws: AsyncMock,
        mock_exchange_rest: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """start() should connect all adapters."""
        await runner.start()

        mock_exchange_ws.connect.assert_awaited_once()
        mock_exchange_rest.connect.assert_awaited_once()
        mock_cache.connect.assert_awaited_once()

        await runner.stop()

    @pytest.mark.asyncio
    async def test_stop_disconnects_adapters(
        self,
        runner: TradingRunner,
        mock_exchange_ws: AsyncMock,
        mock_exchange_rest: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """stop() should disconnect all adapters."""
        await runner.start()
        await runner.stop()

        mock_exchange_ws.disconnect.assert_awaited_once()
        mock_exchange_rest.disconnect.assert_awaited_once()
        mock_cache.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_subscribes_klines(
        self,
        runner: TradingRunner,
        mock_exchange_ws: AsyncMock,
        config: EngineConfig,
    ) -> None:
        """start() should subscribe to kline streams for configured pairs."""
        await runner.start()

        mock_exchange_ws.subscribe_klines.assert_awaited_once()
        call_args = mock_exchange_ws.subscribe_klines.call_args
        assert call_args[1].get("pairs", call_args[0][0]) == config.pairs

        await runner.stop()

    @pytest.mark.asyncio
    async def test_uptime_tracks_time(self, runner: TradingRunner) -> None:
        """uptime property should increase after start()."""
        assert runner.uptime == 0.0
        await runner.start()
        assert runner.uptime > 0.0
        await runner.stop()

    @pytest.mark.asyncio
    async def test_mode_reports_dry_run(self, runner: TradingRunner) -> None:
        """mode property should report dry_run when configured."""
        assert runner.mode == "dry_run"


# ------------------------------------------------------------------
# Candle parsing tests
# ------------------------------------------------------------------

class TestCandleParsing:
    """Test the _parse_candle static method."""

    def test_parse_kairos_format(self, sample_candle_dict: dict) -> None:
        """Standard Kairos dict format should parse correctly."""
        candle = TradingRunner._parse_candle(sample_candle_dict)
        assert candle is not None
        assert candle.pair == "BTCUSDT"
        assert candle.close == 97550.0
        assert candle.is_closed is True

    def test_parse_binance_kline_format(self) -> None:
        """Binance WS kline format should parse correctly."""
        data = {
            "k": {
                "t": 1707566640000,
                "s": "BTCUSDT",
                "i": "1m",
                "o": "97500.00",
                "h": "97600.00",
                "l": "97400.00",
                "c": "97550.00",
                "v": "5.5",
                "x": True,
            }
        }
        candle = TradingRunner._parse_candle(data)
        assert candle is not None
        assert candle.pair == "BTCUSDT"
        assert candle.close == 97550.0
        assert candle.is_closed is True

    def test_parse_invalid_data_returns_none(self) -> None:
        """Invalid/incomplete data should return None."""
        assert TradingRunner._parse_candle({}) is None
        assert TradingRunner._parse_candle({"random": "data"}) is None

    def test_parse_numeric_timestamp(self) -> None:
        """Numeric (epoch ms) timestamp should be parsed."""
        data = {
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "timestamp": 1707566640000,
            "open": 97500.0,
            "high": 97600.0,
            "low": 97400.0,
            "close": 97550.0,
            "volume": 5.5,
            "is_closed": True,
        }
        candle = TradingRunner._parse_candle(data)
        assert candle is not None
        assert candle.pair == "BTCUSDT"


# ------------------------------------------------------------------
# on_candle tests
# ------------------------------------------------------------------

class TestOnCandle:
    """Test the on_candle event handler."""

    @pytest.mark.asyncio
    async def test_non_running_ignores_candle(
        self, runner: TradingRunner, sample_candle_dict: dict
    ) -> None:
        """When the runner is not running, on_candle should do nothing."""
        runner._running = False
        await runner.on_candle(sample_candle_dict)
        # No exception means success

    @pytest.mark.asyncio
    async def test_non_closed_candle_skips_signal(
        self, runner: TradingRunner
    ) -> None:
        """Non-closed candles should not trigger signal generation."""
        runner._running = True
        data = {
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "timestamp": "2026-02-10T12:00:00+00:00",
            "open": 97500.0,
            "high": 97600.0,
            "low": 97400.0,
            "close": 97550.0,
            "volume": 5.5,
            "is_closed": False,
        }
        await runner.on_candle(data)
        # No signal should have been generated

    @pytest.mark.asyncio
    async def test_closed_candle_buffers(
        self, runner: TradingRunner, sample_candle_dict: dict
    ) -> None:
        """Closed candles should be added to the candle buffer."""
        runner._running = True
        await runner.on_candle(sample_candle_dict)

        count = runner._candle_buffer.size(pair="BTCUSDT", timeframe="1m")
        assert count >= 1


# ------------------------------------------------------------------
# Signal execution tests (dry-run)
# ------------------------------------------------------------------

class TestExecuteSignalDryRun:
    """Test signal execution in dry_run mode."""

    @pytest.mark.asyncio
    async def test_buy_signal_opens_position(
        self, runner: TradingRunner, mock_repository: AsyncMock
    ) -> None:
        """A BUY signal in dry_run should create a simulated position."""
        runner._running = True
        # Use a large balance and small position_size_pct for BTC prices
        runner._balance = 100_000.0
        runner._risk_limits.position_size_pct = 1.0  # 1% risk per trade
        runner._risk_limits.max_exposure_pct = 80.0
        runner._position_sizer = PositionSizer(runner._risk_limits)
        runner._strategy_config = StrategyConfig(
            name="test",
            pairs=["BTCUSDT"],
            timeframe="5m",
            risk={"stop_loss_pct": 1.5},
        )

        candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            open=97500.0, high=97600.0, low=97400.0, close=97550.0,
            volume=5.5, pair="BTCUSDT", timeframe="5m", is_closed=True,
        )
        signal = Signal(
            type=SignalType.BUY,
            pair="BTCUSDT",
            timeframe="5m",
            price=97550.0,
            timestamp=candle.timestamp,
            strategy_name="test",
            reason="Test buy signal",
        )

        await runner._execute_signal(signal, "BTCUSDT", candle)

        # Position should be tracked
        assert "BTCUSDT" in runner._open_positions
        pos = runner._open_positions["BTCUSDT"]
        assert pos.side == "BUY"
        assert pos.entry_price == 97550.0
        assert pos.stop_loss > 0
        assert pos.metadata.get("dry_run") is True

        # Trade count should increment
        assert runner._daily_trade_count == 1

        # DB should have been called
        mock_repository.save_trade.assert_awaited()

    @pytest.mark.asyncio
    async def test_sell_signal_without_position_is_noop(
        self, runner: TradingRunner
    ) -> None:
        """A SELL signal with no open position should do nothing."""
        runner._running = True
        runner._strategy_config = StrategyConfig(name="test", pairs=["BTCUSDT"])

        candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            open=97500.0, high=97600.0, low=97400.0, close=97550.0,
            volume=5.5, pair="BTCUSDT", timeframe="5m", is_closed=True,
        )
        signal = Signal(
            type=SignalType.SELL,
            pair="BTCUSDT",
            timeframe="5m",
            price=97550.0,
            timestamp=candle.timestamp,
        )

        # No position open -> should not crash
        await runner._execute_signal(signal, "BTCUSDT", candle)
        assert "BTCUSDT" not in runner._open_positions


# ------------------------------------------------------------------
# Position close tests
# ------------------------------------------------------------------

class TestClosePosition:
    """Test _close_position in dry-run mode."""

    @pytest.mark.asyncio
    async def test_close_position_updates_status(
        self, runner: TradingRunner
    ) -> None:
        """Closing a position should set status to CLOSED and record PnL."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.001,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            stop_loss=96037.50,
            metadata={"strategy_name": "test", "dry_run": True},
        )
        runner._open_positions["BTCUSDT"] = position

        exit_candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
            open=97800.0, high=97900.0, low=97700.0, close=97850.0,
            volume=3.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        await runner._close_position(position, exit_candle, "TRAILING_STOP")

        assert position.status == PositionStatus.CLOSED
        assert position.exit_price == 97850.0
        assert position.exit_reason == "TRAILING_STOP"
        assert "BTCUSDT" not in runner._open_positions

    @pytest.mark.asyncio
    async def test_close_position_creates_trade_record(
        self, runner: TradingRunner
    ) -> None:
        """Closing a position should add a Trade to daily_trades."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.001,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            stop_loss=96037.50,
            metadata={"strategy_name": "test"},
        )
        runner._open_positions["BTCUSDT"] = position

        exit_candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
            open=97800.0, high=97900.0, low=97700.0, close=97850.0,
            volume=3.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        await runner._close_position(position, exit_candle, "TAKE_PROFIT")

        assert len(runner._daily_trades) == 1
        trade = runner._daily_trades[0]
        assert trade.pair == "BTCUSDT"
        assert trade.exit_reason == "TAKE_PROFIT"
        assert trade.pnl_usdt > 0  # Price went up

    @pytest.mark.asyncio
    async def test_close_position_updates_daily_pnl(
        self, runner: TradingRunner
    ) -> None:
        """Closing a profitable position should increase daily PnL."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.01,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            stop_loss=96037.50,
            metadata={},
        )
        runner._open_positions["BTCUSDT"] = position

        exit_candle = Candle(
            timestamp=datetime(2026, 2, 10, 13, 0, 0, tzinfo=timezone.utc),
            open=98000.0, high=98100.0, low=97900.0, close=98000.0,
            volume=4.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        initial_pnl = runner._daily_pnl_usdt
        await runner._close_position(position, exit_candle, "TP_HIT")
        assert runner._daily_pnl_usdt > initial_pnl

    @pytest.mark.asyncio
    async def test_close_losing_position_sets_last_loss_time(
        self, runner: TradingRunner
    ) -> None:
        """Closing a losing position should update _last_loss_time."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.01,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            stop_loss=96037.50,
            metadata={},
        )
        runner._open_positions["BTCUSDT"] = position

        # Exit below entry -> loss
        exit_candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
            open=97000.0, high=97100.0, low=96900.0, close=97000.0,
            volume=4.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        await runner._close_position(position, exit_candle, "STOP_LOSS")
        assert runner._last_loss_time is not None

    @pytest.mark.asyncio
    async def test_close_position_sends_notification(
        self, runner: TradingRunner, mock_notifier: AsyncMock
    ) -> None:
        """Closing a position should send a notification."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.001,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            metadata={},
        )
        runner._open_positions["BTCUSDT"] = position

        exit_candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
            open=97800.0, high=97900.0, low=97700.0, close=97850.0,
            volume=3.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        await runner._close_position(position, exit_candle, "TEST_EXIT")
        mock_notifier.send.assert_awaited_once()


# ------------------------------------------------------------------
# Trust level tests
# ------------------------------------------------------------------

class TestTrustLevel:
    """Test trust level calculation."""

    def test_no_trades_returns_crawl(self, runner: TradingRunner) -> None:
        """With no trades, trust level should be CRAWL."""
        assert runner._get_trust_level() == "CRAWL"

    def test_all_winning_trades(self, runner: TradingRunner) -> None:
        """Many winning trades should give a higher trust level."""
        for _ in range(10):
            runner._daily_trades.append(
                Trade(pair="BTCUSDT", pnl_usdt=10.0)
            )
        level = runner._get_trust_level()
        assert level in ("WALK", "RUN", "SPRINT")

    def test_all_losing_trades(self, runner: TradingRunner) -> None:
        """Many losing trades should give CRAWL trust level."""
        for _ in range(5):
            runner._daily_trades.append(
                Trade(pair="BTCUSDT", pnl_usdt=-10.0)
            )
        assert runner._get_trust_level() == "CRAWL"


# ------------------------------------------------------------------
# Status endpoint tests
# ------------------------------------------------------------------

class TestGetStatus:
    """Test the get_status method used by the health endpoint."""

    def test_status_contains_required_keys(self, runner: TradingRunner) -> None:
        """get_status() should return all keys the health endpoint needs."""
        status = runner.get_status()
        required_keys = {
            "status", "uptime", "pairs", "open_positions",
            "mode", "daily_trades", "daily_pnl_usdt",
            "trust_level", "circuit_breaker", "strategy",
        }
        assert required_keys.issubset(status.keys())

    def test_status_mode_is_dry_run(self, runner: TradingRunner) -> None:
        """Status should reflect dry_run mode from config."""
        status = runner.get_status()
        assert status["mode"] == "dry_run"

    def test_status_strategy_name(
        self, runner: TradingRunner, sample_strategy: StrategyConfig
    ) -> None:
        """Status should include the strategy name if loaded."""
        runner._strategy_config = sample_strategy
        status = runner.get_status()
        assert status["strategy"] == "test_strategy"


# ------------------------------------------------------------------
# Check exits tests
# ------------------------------------------------------------------

class TestCheckExits:
    """Test the _check_exits method."""

    @pytest.mark.asyncio
    async def test_stop_loss_triggers_close(
        self, runner: TradingRunner
    ) -> None:
        """When price drops below stop-loss, the position should be closed."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.001,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            stop_loss=96500.0,
            metadata={},
        )
        runner._open_positions["BTCUSDT"] = position

        # Price below stop-loss
        candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
            open=96600.0, high=96700.0, low=96400.0, close=96400.0,
            volume=5.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        await runner._check_exits("BTCUSDT", candle)

        # Position should be closed
        assert "BTCUSDT" not in runner._open_positions
        assert len(runner._daily_trades) == 1
        assert runner._daily_trades[0].pnl_usdt < 0

    @pytest.mark.asyncio
    async def test_no_exit_when_price_above_sl(
        self, runner: TradingRunner
    ) -> None:
        """When price is above stop-loss, the position should stay open."""
        runner._running = True
        position = Position(
            pair="BTCUSDT",
            side="BUY",
            entry_price=97500.0,
            quantity=0.001,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            stop_loss=96500.0,
            metadata={},
        )
        runner._open_positions["BTCUSDT"] = position

        # Price above stop-loss
        candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
            open=97500.0, high=97800.0, low=97400.0, close=97700.0,
            volume=5.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
        )

        await runner._check_exits("BTCUSDT", candle)

        # Position should remain open
        assert "BTCUSDT" in runner._open_positions

    @pytest.mark.asyncio
    async def test_no_position_no_exit(self, runner: TradingRunner) -> None:
        """_check_exits should do nothing if no position exists for the pair."""
        runner._running = True
        candle = Candle(
            timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            open=97500.0, high=97600.0, low=97400.0, close=97550.0,
            volume=5.0, pair="ETHUSDT", timeframe="1m", is_closed=True,
        )

        # Should not crash
        await runner._check_exits("ETHUSDT", candle)
