"""Integration tests for the trading engine flow.

These tests verify the full pipeline from receiving candles to
generating signals to executing orders, using mocked adapters
but real core components.

Flow tested:
    candles -> TimeframeAggregator -> Indicators -> StrategyEvaluator
    -> SignalFilter -> PortfolioManager -> PositionSizer -> Execute
    -> PositionManager -> Close -> Trade record
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import (
    Candle,
    Position,
    PositionStatus,
    RiskLimits,
    Signal,
    SignalType,
    StrategyConfig,
    Trade,
)
from core.risk.portfolio import PortfolioManager
from core.risk.position import PositionManager
from core.risk.sizing import PositionSizer
from core.strategy.evaluator import StrategyEvaluator
from core.strategy.filters import SignalFilter
from core.timeframe.aggregator import TimeframeAggregator
from core.timeframe.buffer import CandleBuffer
from engine.config import EngineConfig
from engine.runner import TradingRunner


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_1m_candles(
    count: int,
    pair: str = "BTCUSDT",
    start_price: float = 97500.0,
    start_time: datetime | None = None,
) -> list[dict[str, any]]:
    """Generate a sequence of 1m candle dicts for feeding into on_candle."""
    import random
    rng = random.Random(42)

    if start_time is None:
        start_time = datetime(2026, 2, 10, 0, 0, 0, tzinfo=timezone.utc)

    candles = []
    price = start_price

    for i in range(count):
        change = rng.uniform(-0.002, 0.002)
        open_p = round(price, 2)
        close_p = round(open_p * (1 + change), 2)
        high_p = round(max(open_p, close_p) + abs(rng.gauss(0, 10)), 2)
        low_p = round(min(open_p, close_p) - abs(rng.gauss(0, 10)), 2)
        low_p = max(low_p, round(min(open_p, close_p) * 0.999, 2))
        vol = round(rng.uniform(1, 20), 4)

        ts = start_time + timedelta(minutes=i)

        candles.append({
            "pair": pair,
            "timeframe": "1m",
            "timestamp": ts.isoformat(),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": vol,
            "is_closed": True,
        })

        price = close_p

    return candles


def _make_runner(
    dry_run: bool = True,
    pairs: list[str] | None = None,
) -> tuple[TradingRunner, AsyncMock, AsyncMock, AsyncMock]:
    """Create a TradingRunner with mocked adapters for integration tests."""
    config = EngineConfig(
        pairs=pairs or ["BTCUSDT"],
        dry_run=dry_run,
        capital_per_pair=100_000.0,
        base_timeframe="1m",
        strategy_timeframe="5m",
        stop_loss_pct=1.5,
        trailing_activation_pct=0.6,
        trailing_distance_pct=0.3,
        max_positions=3,
        max_daily_loss_pct=5.0,
        max_daily_trades=20,
    )

    mock_repo = AsyncMock()
    mock_repo.get_active_strategy = AsyncMock(return_value=None)
    mock_repo.save_trade = AsyncMock(return_value="trade-id")
    mock_repo.save_daily_stats = AsyncMock()

    mock_cache = AsyncMock()
    mock_cache.connect = AsyncMock()
    mock_cache.disconnect = AsyncMock()
    mock_cache.cache_bot_status = AsyncMock()

    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock()

    runner = TradingRunner(
        config=config,
        exchange_ws=None,
        exchange_rest=None,
        repository=mock_repo,
        cache=mock_cache,
        notifier=mock_notifier,
    )

    # Use a realistic position_size_pct for BTC-level prices
    runner._risk_limits.position_size_pct = 1.0
    runner._risk_limits.max_exposure_pct = 80.0
    runner._position_sizer = PositionSizer(runner._risk_limits)

    return runner, mock_repo, mock_cache, mock_notifier


# ------------------------------------------------------------------
# Integration tests: Full pipeline with mocked adapters
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_candle_pipeline_buffers_correctly() -> None:
    """Feeding 1m candles should populate the candle buffer properly."""
    runner, _, _, _ = _make_runner()
    runner._running = True
    runner._strategy_config = StrategyConfig(
        name="test", pairs=["BTCUSDT"], timeframe="5m",
        indicators_needed=[], is_active=True,
    )

    candles = _make_1m_candles(10)
    for c in candles:
        await runner.on_candle(c)

    # 1m candles should be buffered
    buf_count = runner._candle_buffer.size(pair="BTCUSDT", timeframe="1m")
    assert buf_count == 10


@pytest.mark.asyncio
async def test_timeframe_aggregation_produces_5m() -> None:
    """After 5 x 1m candles, the aggregator should produce a 5m candle."""
    runner, _, _, _ = _make_runner()
    runner._running = True
    runner._strategy_config = StrategyConfig(
        name="test", pairs=["BTCUSDT"], timeframe="5m",
        indicators_needed=[], is_active=True,
    )

    # Feed exactly 5 minutes of candles (0:00 to 0:04)
    candles = _make_1m_candles(5)
    for c in candles:
        await runner.on_candle(c)

    # The 5m buffer should have data (the aggregator emits when boundary crossed)
    # We may need one more candle to trigger the boundary
    extra = _make_1m_candles(
        1,
        start_price=97500.0,
        start_time=datetime(2026, 2, 10, 0, 5, 0, tzinfo=timezone.utc),
    )
    await runner.on_candle(extra[0])

    buf_5m = runner._candle_buffer.size(pair="BTCUSDT", timeframe="5m")
    assert buf_5m >= 1


@pytest.mark.asyncio
async def test_dry_run_buy_creates_position() -> None:
    """In dry_run, executing a BUY signal should create a tracked position."""
    runner, mock_repo, _, _ = _make_runner(dry_run=True)
    runner._running = True
    runner._strategy_config = StrategyConfig(
        name="test", pairs=["BTCUSDT"], timeframe="5m",
        risk={"stop_loss_pct": 1.5}, is_active=True,
    )

    signal = Signal(
        type=SignalType.BUY,
        pair="BTCUSDT",
        timeframe="5m",
        price=97500.0,
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        strategy_name="test",
        reason="Integration test buy",
    )

    candle = Candle(
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        open=97450.0, high=97600.0, low=97400.0, close=97500.0,
        volume=5.0, pair="BTCUSDT", timeframe="5m", is_closed=True,
    )

    await runner._execute_signal(signal, "BTCUSDT", candle)

    # Position should exist
    assert "BTCUSDT" in runner._open_positions
    pos = runner._open_positions["BTCUSDT"]
    assert pos.side == "BUY"
    assert pos.entry_price == 97500.0
    assert pos.stop_loss == pytest.approx(97500.0 * 0.985, rel=0.001)
    assert pos.quantity > 0

    # DB save should have been called
    mock_repo.save_trade.assert_awaited()


@pytest.mark.asyncio
async def test_exit_conditions_trigger_close() -> None:
    """When stop-loss is hit, the position should be closed automatically."""
    runner, _, _, mock_notifier = _make_runner(dry_run=True)
    runner._running = True

    # Place a position
    position = Position(
        pair="BTCUSDT",
        side="BUY",
        entry_price=97500.0,
        quantity=0.01,
        entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        stop_loss=96000.0,
        metadata={"strategy_name": "test"},
    )
    runner._open_positions["BTCUSDT"] = position

    # Feed a candle that drops below stop-loss
    sl_candle = Candle(
        timestamp=datetime(2026, 2, 10, 12, 30, 0, tzinfo=timezone.utc),
        open=96100.0, high=96200.0, low=95800.0, close=95900.0,
        volume=10.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
    )

    await runner._check_exits("BTCUSDT", sl_candle)

    # Position should be closed
    assert "BTCUSDT" not in runner._open_positions
    assert len(runner._daily_trades) == 1
    trade = runner._daily_trades[0]
    assert trade.pnl_usdt < 0  # It was a loss
    assert "STOP_LOSS" in trade.exit_reason

    # Notification should have been sent
    mock_notifier.send.assert_awaited()


@pytest.mark.asyncio
async def test_circuit_breaker_pauses_trading() -> None:
    """After 3 consecutive losses, the circuit breaker should block new trades."""
    runner, _, _, _ = _make_runner(dry_run=True)
    runner._running = True
    runner._strategy_config = StrategyConfig(
        name="test",
        pairs=["BTCUSDT"],
        timeframe="5m",
        risk={"stop_loss_pct": 1.5},
        entry_conditions={
            "logic": "AND",
            "conditions": [
                {"indicator": "rsi", "operator": "below", "value": 30},
            ],
        },
        indicators_needed=["rsi"],
        is_active=True,
    )

    # Simulate 3 consecutive losses
    for i in range(3):
        runner._daily_trades.append(
            Trade(
                pair="BTCUSDT",
                pnl_usdt=-10.0,
                exit_time=datetime(2026, 2, 10, 12, i, 0, tzinfo=timezone.utc),
            )
        )

    # Check circuit breaker through the portfolio manager
    cb_ok, cb_reason = runner._portfolio_manager.check_circuit_breakers(
        runner._daily_trades,
        runner._daily_pnl_pct(),
        runner._balance,
    )
    assert cb_ok is False
    assert "consecutive" in cb_reason.lower()


@pytest.mark.asyncio
async def test_full_trade_lifecycle_dry_run() -> None:
    """Full lifecycle: BUY -> position opened -> price drop -> SL hit -> SELL.

    This tests the entire pipeline in dry_run mode without any real exchange.
    """
    runner, mock_repo, _, mock_notifier = _make_runner(dry_run=True)
    runner._running = True
    runner._strategy_config = StrategyConfig(
        name="test_lifecycle",
        pairs=["BTCUSDT"],
        timeframe="5m",
        risk={
            "stop_loss_pct": 1.5,
            "trailing_activation_pct": 0.5,
            "trailing_distance_pct": 0.2,
        },
        is_active=True,
    )

    # Step 1: Open position via BUY signal
    entry_candle = Candle(
        timestamp=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        open=97400.0, high=97600.0, low=97300.0, close=97500.0,
        volume=5.0, pair="BTCUSDT", timeframe="5m", is_closed=True,
    )
    buy_signal = Signal(
        type=SignalType.BUY,
        pair="BTCUSDT",
        timeframe="5m",
        price=97500.0,
        timestamp=entry_candle.timestamp,
        strategy_name="test_lifecycle",
        reason="Lifecycle test entry",
    )

    await runner._execute_signal(buy_signal, "BTCUSDT", entry_candle)
    assert "BTCUSDT" in runner._open_positions
    position = runner._open_positions["BTCUSDT"]
    assert position.entry_price == pytest.approx(97500.0)

    # Step 2: Price goes up slightly (no exit)
    up_candle = Candle(
        timestamp=datetime(2026, 2, 10, 12, 5, 0, tzinfo=timezone.utc),
        open=97550.0, high=97700.0, low=97500.0, close=97650.0,
        volume=3.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
    )
    await runner._check_exits("BTCUSDT", up_candle)
    assert "BTCUSDT" in runner._open_positions  # Still open

    # Step 3: Price drops below stop-loss
    sl_price = position.stop_loss
    drop_candle = Candle(
        timestamp=datetime(2026, 2, 10, 12, 10, 0, tzinfo=timezone.utc),
        open=sl_price + 10, high=sl_price + 50, low=sl_price - 100,
        close=sl_price - 50,
        volume=8.0, pair="BTCUSDT", timeframe="1m", is_closed=True,
    )
    await runner._check_exits("BTCUSDT", drop_candle)

    # Step 4: Verify position is closed with a trade record
    assert "BTCUSDT" not in runner._open_positions
    assert position.status == PositionStatus.CLOSED
    assert len(runner._daily_trades) == 1

    trade = runner._daily_trades[0]
    assert trade.pnl_usdt < 0
    assert "STOP_LOSS" in trade.exit_reason

    # Step 5: Verify persistence and notifications
    assert mock_repo.save_trade.await_count >= 2  # Once for open, once for close
    assert mock_notifier.send.await_count >= 2  # Once for buy, once for sell


@pytest.mark.asyncio
async def test_max_positions_blocks_new_entry() -> None:
    """When max_positions is reached, new BUY signals should be blocked."""
    runner, _, _, _ = _make_runner(dry_run=True)
    runner._running = True
    runner._strategy_config = StrategyConfig(
        name="test", pairs=["BTCUSDT"], timeframe="5m",
        risk={"stop_loss_pct": 1.5}, is_active=True,
    )

    # Fill up to max positions (3)
    for pair in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        runner._open_positions[pair] = Position(
            pair=pair,
            side="BUY",
            entry_price=100.0,
            quantity=1.0,
            entry_time=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

    # Try to check if a new position can be opened
    open_list = list(runner._open_positions.values())
    can_open, reason = runner._portfolio_manager.can_open_position(
        open_list, runner._balance, runner._daily_trade_count,
        runner._daily_pnl_pct(),
    )
    assert can_open is False
    assert "max" in reason.lower() or "Max" in reason


@pytest.mark.asyncio
async def test_daily_stats_calculation() -> None:
    """After some trades, daily stats should calculate correctly."""
    runner, mock_repo, _, _ = _make_runner(dry_run=True)
    runner._running = True

    # Add some trades
    runner._daily_trades = [
        Trade(pair="BTCUSDT", pnl_usdt=15.0),
        Trade(pair="BTCUSDT", pnl_usdt=-5.0),
        Trade(pair="BTCUSDT", pnl_usdt=10.0),
        Trade(pair="BTCUSDT", pnl_usdt=-3.0),
    ]

    stats = runner._portfolio_manager.calculate_daily_stats(runner._daily_trades)

    assert stats["total_trades"] == 4
    assert stats["wins"] == 2
    assert stats["losses"] == 2
    assert stats["win_rate"] == 50.0
    assert stats["total_pnl"] == 17.0
