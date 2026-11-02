"""Trading runner -- orchestrates the main event loop.

The TradingRunner receives candle events from the exchange adapter,
updates indicators, evaluates strategies, checks risk limits, and
executes signals through the exchange adapter.

It depends on abstract interfaces (BaseExchange, BaseRepository) and
core pure-Python modules -- never on concrete adapter implementations.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.config import EngineConfig
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
from core.indicators.registry import IndicatorRegistry, get_registry
from core.strategy.evaluator import StrategyEvaluator
from core.strategy.loader import (
    IndicatorSpec,
    StrategyLoader,
    state_key as loader_state_key,
    trend_filter_specs,
)
from core.strategy.filters import SignalFilter
from core.risk.position import PositionManager
from core.risk.sizing import PositionSizer, SymbolInfo, TRUST_LEVELS
from core.risk.portfolio import PortfolioManager
from core.timeframe.aggregator import TimeframeAggregator
from core.timeframe.buffer import CandleBuffer

logger = logging.getLogger(__name__)

# How often to persist daily stats (seconds).
DAILY_STATS_SAVE_INTERVAL = 300  # 5 minutes

# How often to cache engine state to Redis (seconds).
STATE_CACHE_INTERVAL = 10


def _as_utc(value: datetime) -> datetime:
    """Timezone-aware UTC datetime (naive values are assumed to be UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _naive(value: datetime | None) -> datetime | None:
    """Drop tzinfo: DB timestamp columns are naive (UTC)."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class TradingRunner:
    """Event-driven trading engine runner.

    Orchestrates the full pipeline:
        Binance WS candle -> TimeframeAggregator -> Indicators.calculate()
        -> Strategy.evaluate() -> SignalFilter.apply() -> RiskManager.validate()
        -> PositionSizer.calculate() -> Binance REST order -> Position tracking
        -> DB save -> Notifications

    Parameters
    ----------
    config : EngineConfig
        Engine configuration.
    exchange_ws :
        WebSocket exchange adapter (BaseExchange) for streaming.
    exchange_rest :
        REST exchange adapter (BaseExchange) for order execution.
    repository :
        Database repository (BaseRepository) for persistence.
    cache :
        Redis cache adapter for caching and pub/sub.
    notifier :
        Notification adapter (Telegram, Firebase, etc.).
    """

    def __init__(
        self,
        config: EngineConfig,
        exchange_ws: Any = None,
        exchange_rest: Any = None,
        repository: Any = None,
        cache: Any = None,
        notifier: Any = None,
    ) -> None:
        self._config = config
        self._exchange_ws = exchange_ws
        self._exchange_rest = exchange_rest
        self._repository = repository
        self._cache = cache
        self._notifier = notifier

        # ---- Core components ----
        self._risk_limits = RiskLimits(
            max_positions=config.max_positions,
            max_daily_loss_pct=config.max_daily_loss_pct,
            max_drawdown_pct=config.max_drawdown_pct,
            max_daily_trades=config.max_daily_trades,
        )

        self._indicator_registry: IndicatorRegistry = get_registry()
        self._strategy_loader = StrategyLoader()
        self._strategy_evaluator = StrategyEvaluator()
        self._signal_filter = SignalFilter()
        self._position_manager = PositionManager()
        self._position_sizer = PositionSizer(self._risk_limits)
        self._portfolio_manager = PortfolioManager(self._risk_limits)
        # TimeframeAggregator is created lazily after strategy is loaded,
        # because the strategy may override the timeframe.
        self._timeframe_aggregator: TimeframeAggregator | None = None
        self._effective_strategy_tf: str = config.strategy_timeframe
        self._candle_buffer = CandleBuffer(max_size=1000)

        # ---- Active strategy ----
        self._strategy_config: StrategyConfig | None = None

        # ---- Internal state ----
        self._running = False
        self._start_time: float = 0.0
        self._open_positions: dict[str, Position] = {}  # pair -> Position
        self._indicator_states: dict[str, dict[str, Any]] = {}  # pair -> {state_key: state}
        # (strategy_config, specs) -- see _get_indicator_specs()
        self._indicator_specs_cache: tuple[Any, dict[str, IndicatorSpec]] | None = None
        self._daily_trades: list[Trade] = []
        self._daily_trade_count: int = 0
        self._daily_pnl_usdt: float = 0.0
        self._recent_signals: list[Signal] = []
        self._last_loss_time: datetime | None = None
        self._balance: float = config.capital_per_pair * len(config.pairs)

        # Exchange symbol info cache: pair -> SymbolInfo
        self._symbol_info: dict[str, SymbolInfo] = {}

        # Tracking for periodic saves
        self._last_stats_save: float = 0.0
        self._last_state_cache: float = 0.0

        # Counter for periodic INFO logging.
        self._candle_count: int = 0
        self._strategy_eval_count: int = 0

        # Pairs currently being closed by _close_position (prevents
        # duplicate saves when the WS fill event arrives during the await).
        self._pending_close: set[str] = set()

        # Circuit breaker state
        self._circuit_breaker_active = False
        self._circuit_breaker_reason = ""
        self._circuit_breaker_until: datetime | None = None
        # UTC day of the daily counters (None until the first closed candle).
        self._stats_day: Any = None
        # Losses before this index of _daily_trades were already "paid" by a
        # circuit-breaker pause and must not re-trip it.
        self._cb_trades_offset: int = 0

    # ------------------------------------------------------------------
    # Properties for external monitoring (health endpoint)
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def uptime(self) -> float:
        """Uptime in seconds since start()."""
        if self._start_time <= 0:
            return 0.0
        return time.monotonic() - self._start_time

    @property
    def open_positions_count(self) -> int:
        return len(self._open_positions)

    @property
    def mode(self) -> str:
        return "dry_run" if self._config.dry_run else "live"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the trading engine.

        Steps:
        1. Discover and register all indicator implementations
        2. Load the active strategy from config/DB
        3. Connect all adapters (exchange, database, cache, notifier)
        4. Fetch exchange info for configured pairs
        5. Warm up indicators with historical candles
        6. Subscribe to WebSocket streams
        7. Mark the engine as running
        """
        logger.info("Starting TradingRunner...")
        self._start_time = time.monotonic()

        # Step 1: Discover indicators
        try:
            self._indicator_registry.discover()
            logger.info(
                "Indicator registry: %d indicators loaded",
                len(self._indicator_registry),
            )
        except Exception as exc:
            logger.warning("Indicator discovery warning: %s", exc)

        # Step 2: Load active strategy
        await self._load_strategy()

        # Step 3: Connect adapters
        if self._exchange_ws is not None:
            try:
                await self._exchange_ws.connect()
                logger.info("Exchange WebSocket connected")
            except Exception as exc:
                logger.error("Failed to connect Exchange WS: %s", exc)

        if self._exchange_rest is not None:
            try:
                await self._exchange_rest.connect()
                logger.info("Exchange REST connected")
            except Exception as exc:
                logger.error("Failed to connect Exchange REST: %s", exc)

        if self._cache is not None:
            try:
                await self._cache.connect()
                logger.info("Redis cache connected")
            except Exception as exc:
                logger.warning("Redis connection failed (non-fatal): %s", exc)

        # Step 3b: Fetch real USDT balance from Binance
        if self._exchange_rest is not None and not self._config.dry_run:
            try:
                real_balance = await self._exchange_rest.get_balance("USDT")
                if real_balance > 0:
                    self._balance = real_balance
                    logger.info("Binance USDT balance loaded: %.2f", real_balance)
            except Exception as exc:
                logger.warning("Could not fetch Binance balance: %s", exc)

        # Step 3c: Restore open positions from DB
        await self._restore_open_positions()

        # Step 3d: Restore today's daily stats from DB
        await self._restore_daily_stats()

        # Step 4: Fetch exchange info and warm up indicators
        for pair in self._config.pairs:
            await self._initialize_pair(pair)

        # Step 5: Subscribe to streams
        if self._exchange_ws is not None:
            try:
                await self._exchange_ws.subscribe_klines(
                    self._config.pairs,
                    self._config.base_timeframe,
                    self.on_candle,
                )
                logger.info(
                    "Subscribed to klines: pairs=%s, tf=%s",
                    self._config.pairs, self._config.base_timeframe,
                )
            except Exception as exc:
                logger.error("Failed to subscribe to klines: %s", exc)

            # Account events (fills, balances) only matter in live mode: in
            # dry-run they would mix the real account into the simulation.
            if not self._config.dry_run:
                try:
                    await self._exchange_ws.subscribe_user_data(self.on_user_data)
                    logger.info("Subscribed to user data stream")
                except Exception as exc:
                    logger.warning("Failed to subscribe to user data: %s", exc)

        self._running = True
        logger.info(
            "TradingRunner started: pairs=%s, mode=%s, strategy=%s",
            self._config.pairs,
            self.mode,
            self._strategy_config.name if self._strategy_config else "none",
        )

    async def stop(self) -> None:
        """Gracefully stop the trading engine.

        Steps:
        1. Mark as not running (no new signals will be processed)
        2. Save final state to cache and DB
        3. Disconnect all adapters
        """
        logger.info("Stopping TradingRunner...")
        self._running = False

        # Save final state
        await self._save_state_to_cache()
        await self._save_daily_stats()

        # Disconnect adapters (in reverse order of connection)
        if self._exchange_ws is not None:
            try:
                await self._exchange_ws.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting WS: %s", exc)

        if self._exchange_rest is not None:
            try:
                await self._exchange_rest.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting REST: %s", exc)

        if self._cache is not None:
            try:
                await self._cache.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting cache: %s", exc)

        logger.info("TradingRunner stopped.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_candle(self, candle_data: dict[str, Any]) -> None:
        """Handle an incoming candle event from the exchange.

        This is the main event handler that drives the trading logic.

        Pipeline:
        1. Parse raw candle dict into Candle model
        2. Update timeframe aggregator (build higher TF from 1m)
        3. Buffer candles for indicator lookback
        4. Update indicators for all completed timeframes
        5. Evaluate strategy conditions
        6. Apply post-signal filters
        7. If signal is actionable -> check risk limits -> execute
        8. Check all open positions for exits
        9. Cache state periodically

        Parameters
        ----------
        candle_data : dict
            Raw candle data with keys: pair, timeframe, timestamp,
            open, high, low, close, volume, is_closed.
        """
        if not self._running:
            return

        # Parse the incoming candle
        candle = self._parse_candle(candle_data)
        if candle is None:
            return

        pair = candle.pair

        # Always buffer the base-timeframe candle
        self._candle_buffer.add(candle)

        # Only process closed candles for signal generation
        if not candle.is_closed:
            # Update trailing stops on live price tick
            await self._update_trailing_on_tick(pair, candle.close, candle.timestamp)
            return

        self._candle_count += 1
        await self._roll_daily_stats(candle.timestamp)
        # Periodic INFO log every 10 closed candles for monitoring.
        if self._candle_count % 10 == 0:
            logger.info(
                "Heartbeat: %d candles processed, %d strategy evals, "
                "%d trades today, positions=%d",
                self._candle_count,
                self._strategy_eval_count,
                self._daily_trade_count,
                len(self._open_positions),
            )

        completed_candles: list[Candle] = []
        if self._timeframe_aggregator is not None:
            # Aggregate 1m candles into the higher timeframes (e.g. 5m, 15m).
            completed_candles = self._timeframe_aggregator.on_candle(candle)
            for htf_candle in completed_candles:
                self._candle_buffer.add(htf_candle)
        if self._effective_strategy_tf == candle.timeframe:
            completed_candles.append(candle)

        # Multi-timeframe: refresh the indicators of the other timeframes
        # first, so the strategy candle closing on the same minute sees them.
        strategy_candle = None
        for htf_candle in completed_candles:
            if htf_candle.timeframe == self._effective_strategy_tf:
                strategy_candle = htf_candle
            else:
                self._update_indicators(pair, htf_candle)
        if strategy_candle is not None:
            await self._process_strategy_candle(pair, strategy_candle)

        # Step 4: Check exits on the base-TF candle price
        await self._check_exits(pair, candle)

        # Step 5: Periodic state caching
        now = time.monotonic()
        if now - self._last_state_cache > STATE_CACHE_INTERVAL:
            await self._save_state_to_cache()
            self._last_state_cache = now

        if now - self._last_stats_save > DAILY_STATS_SAVE_INTERVAL:
            await self._save_daily_stats()
            self._last_stats_save = now

    async def on_user_data(self, data: dict[str, Any]) -> None:
        """Handle user-data stream events (fills, balance updates).

        Parameters
        ----------
        data : dict
            User-data event from the exchange.  Event types include:
            - executionReport: order fill or status change
            - outboundAccountPosition: balance update
        """
        if not self._running:
            return

        event_type = data.get("e", "")

        if event_type == "executionReport":
            await self._handle_order_update(data)
        elif event_type == "outboundAccountPosition":
            await self._handle_balance_update(data)
        else:
            logger.debug("Unhandled user-data event: %s", event_type)

    # ------------------------------------------------------------------
    # Main pipeline processing
    # ------------------------------------------------------------------

    async def _process_strategy_candle(self, pair: str, candle: Candle) -> None:
        """Run the full strategy pipeline on a completed strategy-TF candle.

        This is the core decision-making path:
        indicators -> strategy evaluation -> filtering -> risk check -> execution.
        """
        if self._strategy_config is None:
            return

        # Check circuit breakers first
        # Market time (candle) drives the breaker: same as wall clock in live,
        # and correct when candles are replayed.
        now = _as_utc(candle.timestamp)
        if self._circuit_breaker_active:
            if self._circuit_breaker_until and now < self._circuit_breaker_until:
                logger.debug("Circuit breaker active: %s", self._circuit_breaker_reason)
                return
            else:
                self._circuit_breaker_active = False
                self._circuit_breaker_reason = ""
                self._circuit_breaker_until = None
                # Start a fresh losing streak after the pause, otherwise the
                # same 3 losses re-trip the breaker forever.
                self._cb_trades_offset = len(self._daily_trades)
                logger.info("Circuit breaker cleared")

        self._strategy_eval_count += 1

        # Step 1: Update indicators
        indicator_states = self._update_indicators(pair, candle)

        # Step 2: Build evaluation context
        has_position = pair in self._open_positions
        context = {
            "pair": pair,
            "timeframe": self._effective_strategy_tf,
            "price": candle.close,
            "timestamp": candle.timestamp,
            "has_position": has_position,
        }

        # Step 3: Evaluate strategy
        signal = self._strategy_evaluator.evaluate(
            self._strategy_config, indicator_states, context
        )

        if not signal.is_actionable:
            return

        logger.info(
            "Signal generated: %s %s at %.2f (reason: %s)",
            signal.type.value, pair, signal.price, signal.reason,
        )

        # Step 4: Apply post-signal filters -- entries only. Filters (trend,
        # EMA, cooldown...) must never block an exit: a SELL closes an open
        # long position and has to go through.
        if signal.type == SignalType.BUY:
            candles_for_filter = self._candle_buffer.get_last(
                100, pair=pair, timeframe=self._effective_strategy_tf
            )
            filter_config = self._strategy_config.filters or {}
            signal = self._signal_filter.apply_filters(signal, candles_for_filter, filter_config)

            if not signal.is_actionable:
                logger.info("Signal filtered out: %s", signal.reason)
                return

            # Legacy filter check (EMA trend, ADX trend, trading hours, loss
            # cooldown, etc.) using the indicator states computed with the
            # filter's own period.
            trend = trend_filter_specs(self._strategy_config.filters)
            ema_key = loader_state_key(*trend.get("ema_trend", ("ema", None)))
            adx_key = loader_state_key(*trend.get("adx_trend", ("adx_dmi", None)))
            ema_trend_value = self._latest_indicator_value(pair, ema_key, "ema") or 0.0
            adx_value = self._latest_indicator_value(pair, adx_key, "adx")

            legacy_context = {
                "price": candle.close,
                "timestamp": candle.timestamp,
                "daily_trade_count": self._daily_trade_count,
                "daily_pnl_pct": self._daily_pnl_pct(),
                "last_loss_time": self._last_loss_time,
                "ema_trend_value": ema_trend_value,
                "adx_value": adx_value,
            }
            passed, reason = self._signal_filter.check_all(self._strategy_config, legacy_context)
            if not passed:
                logger.info("Signal rejected by legacy filter: %s", reason)
                return

        # Step 5: Check portfolio constraints
        if signal.type == SignalType.BUY:
            open_positions_list = list(self._open_positions.values())
            can_open, reason = self._portfolio_manager.can_open_position(
                open_positions_list,
                self._balance,
                self._daily_trade_count,
                self._daily_pnl_pct(),
            )
            if not can_open:
                logger.info("Position blocked by portfolio manager: %s", reason)
                return

            # Check circuit breakers
            cb_ok, cb_reason = self._portfolio_manager.check_circuit_breakers(
                self._daily_trades[self._cb_trades_offset:],
                self._daily_pnl_pct(),
                self._balance,
            )
            if not cb_ok:
                logger.warning("Circuit breaker tripped: %s", cb_reason)
                self._circuit_breaker_active = True
                self._circuit_breaker_reason = cb_reason
                # Pause 30 min for consecutive losses, 24h for large loss
                if "consecutive" in cb_reason.lower():
                    self._circuit_breaker_until = now + timedelta(minutes=30)
                else:
                    self._circuit_breaker_until = now + timedelta(hours=24)
                return

        # Step 6: Execute signal
        self._recent_signals.append(signal)
        if len(self._recent_signals) > 50:
            self._recent_signals = self._recent_signals[-50:]

        await self._execute_signal(signal, pair, candle)

    # ------------------------------------------------------------------
    # Indicator management
    # ------------------------------------------------------------------

    def _update_indicators(
        self, pair: str, candle: Candle
    ) -> dict[str, dict[str, Any]]:
        """Update all indicators required by the active strategy.

        Uses incremental update() if previous state exists,
        otherwise falls back to full calculate() over the buffer.

        Returns the indicator states dict for strategy evaluation.
        """
        if self._strategy_config is None:
            return {}

        if pair not in self._indicator_states:
            self._indicator_states[pair] = {}

        pair_states = self._indicator_states[pair]

        # One state per (indicator, params, timeframe) used by the strategy;
        # only the states of this candle's timeframe are updated.
        for state_key, (ind_key, params, spec_tf) in self._get_indicator_specs().items():
            if (spec_tf or self._effective_strategy_tf) != candle.timeframe:
                continue
            try:
                indicator = self._indicator_registry.get(ind_key)
            except KeyError:
                logger.warning("Indicator %r not registered, skipping", ind_key)
                continue

            prev_state = pair_states.get(state_key)

            try:
                if prev_state is not None:
                    # Incremental update (hot path)
                    new_state = indicator.update(candle, prev_state, **params)
                else:
                    # Full calculation over buffered candles
                    candles = self._candle_buffer.get_all(
                        pair=pair, timeframe=candle.timeframe
                    )
                    if candles:
                        new_state = indicator.calculate(candles, **params)
                    else:
                        new_state = indicator.calculate([candle], **params)

                pair_states[state_key] = new_state

            except Exception as exc:
                logger.error(
                    "Indicator %r update failed for %s: %s",
                    state_key, pair, exc,
                )

        return pair_states

    @property
    def _dry_run_fee_rate(self) -> float:
        """Simulated fee per side as a fraction (0.001 = 0.1 %)."""
        return max(0.0, self._config.dry_run_fee_pct) / 100.0

    def _get_indicator_specs(self) -> dict[str, IndicatorSpec]:
        """Indicator states required by the active strategy (cached per strategy)."""
        if self._strategy_config is None:
            return {}
        cached = self._indicator_specs_cache
        if cached is None or cached[0] is not self._strategy_config:
            specs = self._strategy_loader.indicator_specs(self._strategy_config)
            self._indicator_specs_cache = (self._strategy_config, specs)
            return specs
        return cached[1]

    def _latest_indicator_value(
        self, pair: str, state_key: str, field_name: str
    ) -> float | None:
        """Last non-None value of a list field in an indicator state."""
        state = self._indicator_states.get(pair, {}).get(state_key)
        if not state or not state.get(field_name):
            return None
        for v in reversed(state[field_name]):
            if v is not None:
                return v
        return None

    def _warm_up_indicators(
        self, pair: str, historical: list[Candle], timeframe: str | None = None
    ) -> None:
        """Feed historical candles into indicators to build initial state.

        Parameters
        ----------
        pair : str
            Trading pair being warmed up.
        historical : list[Candle]
            Historical candle data, oldest first.
        timeframe : str, optional
            Timeframe of *historical* (default: the strategy timeframe).
            Only the indicator states of that timeframe are computed.
        """
        if not historical or self._strategy_config is None:
            return
        timeframe = timeframe or self._effective_strategy_tf

        logger.info(
            "Warming up indicators for %s (%s) with %d candles",
            pair, timeframe, len(historical),
        )

        if pair not in self._indicator_states:
            self._indicator_states[pair] = {}

        # Buffer all historical candles
        for c in historical:
            self._candle_buffer.add(c)

        # Calculate initial state for each spec of this timeframe
        for state_key, (ind_key, params, spec_tf) in self._get_indicator_specs().items():
            if (spec_tf or self._effective_strategy_tf) != timeframe:
                continue
            try:
                indicator = self._indicator_registry.get(ind_key)
                state = indicator.calculate(historical, **params)
                self._indicator_states[pair][state_key] = state
            except KeyError:
                logger.warning("Indicator %r not registered, skipping warmup", ind_key)
            except Exception as exc:
                logger.error("Indicator %r warmup failed for %s: %s", state_key, pair, exc)

    # ------------------------------------------------------------------
    # Signal execution
    # ------------------------------------------------------------------

    async def _execute_signal(
        self, signal: Signal, pair: str, candle: Candle
    ) -> None:
        """Execute a trading signal by placing an order.

        Parameters
        ----------
        signal : Signal
            A Signal object from core.models.
        pair : str
            The trading pair.
        candle : Candle
            The current candle (for price reference).
        """
        if signal.type == SignalType.BUY:
            await self._execute_buy(signal, pair, candle)
        elif signal.type in (SignalType.SELL, SignalType.EMERGENCY_SELL):
            # Strategy-generated sell for an open position
            if pair in self._open_positions:
                position = self._open_positions[pair]
                await self._close_position(position, candle, signal.reason)

    async def _execute_buy(
        self, signal: Signal, pair: str, candle: Candle
    ) -> None:
        """Execute a BUY signal: size the position, place order, track.

        Parameters
        ----------
        signal : Signal
            The BUY signal.
        pair : str
            The trading pair.
        candle : Candle
            The current candle.
        """
        entry_price = candle.close
        risk_config = self._strategy_config.risk if self._strategy_config else {}

        # Calculate stop-loss
        sl_pct = risk_config.get("stop_loss_pct", self._config.stop_loss_pct)
        stop_loss_price = entry_price * (1.0 - sl_pct / 100.0)

        # Calculate position size
        symbol_info = self._symbol_info.get(pair)
        quantity = self._position_sizer.calculate_size(
            balance=self._balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            symbol_info=symbol_info,
        )

        # Cap notional to max_position_size_pct of balance.
        max_pct = risk_config.get("max_position_size_pct", 10.0)
        max_notional = self._balance * (max_pct / 100.0)
        if entry_price > 0 and quantity * entry_price > max_notional:
            quantity = max_notional / entry_price
            # Re-clamp to exchange constraints.
            if symbol_info is not None:
                quantity = self._position_sizer._clamp_to_symbol(
                    quantity, entry_price, symbol_info
                )

        if quantity <= 0.0:
            logger.info("Position size is zero for %s, skipping", pair)
            return

        # Validate the order
        valid, reason = self._position_sizer.validate_order(
            self._balance, quantity, entry_price
        )
        if not valid:
            logger.info("Order validation failed for %s: %s", pair, reason)
            return

        # Calculate take-profit levels
        tp_levels = []
        tp_config = risk_config.get("take_profit_levels", [])
        for tp in tp_config:
            tp_pct = tp.get("pct", 0.0)
            if tp_pct > 0:
                tp_price = entry_price * (1.0 + tp_pct / 100.0)
                tp_levels.append({
                    "price": tp_price,
                    "pct_to_close": tp.get("close_pct", 100.0),
                    "hit": False,
                })

        # Trailing stop configuration
        trailing_activation_pct = risk_config.get(
            "trailing_activation_pct", self._config.trailing_activation_pct
        )
        trailing_distance_pct = risk_config.get(
            "trailing_distance_pct", self._config.trailing_distance_pct
        )
        # Optional time-based exit (PositionManager._check_time_based_exit).
        max_hold_minutes = risk_config.get("max_hold_minutes")

        if self._config.dry_run:
            # Dry-run mode: simulate the trade
            logger.info(
                "[DRY-RUN] BUY %s: qty=%.8f at %.2f, SL=%.2f",
                pair, quantity, entry_price, stop_loss_price,
            )
            position = Position(
                pair=pair,
                side="BUY",
                entry_price=entry_price,
                quantity=quantity,
                entry_time=candle.timestamp,
                stop_loss=stop_loss_price,
                take_profit_levels=tp_levels,
                entry_reason=signal.reason,
                metadata={
                    "strategy_name": signal.strategy_name,
                    "trailing_activation_pct": trailing_activation_pct,
                    "trailing_distance_pct": trailing_distance_pct,
                    "max_hold_minutes": max_hold_minutes,
                    "dry_run": True,
                },
            )
            # Simulated cash: debit the cost and the entry fee (live mode
            # gets its balance from the exchange WS instead).
            entry_fee = quantity * entry_price * self._dry_run_fee_rate
            position.metadata["entry_fee"] = entry_fee
            self._balance -= quantity * entry_price + entry_fee

            self._open_positions[pair] = position
            self._daily_trade_count += 1

            # Save to DB
            await self._save_trade_to_db(position, "OPEN")

            # Notify
            await self._send_notification(
                f"[DRY-RUN] BUY {pair}\n"
                f"Price: {entry_price:.2f}\n"
                f"Qty: {quantity:.8f}\n"
                f"SL: {stop_loss_price:.2f}\n"
                f"Reason: {signal.reason}"
            )
            return

        # Live mode: place market order
        try:
            order_result = await self._exchange_rest.place_order(
                pair=pair,
                side="BUY",
                quantity=quantity,
                order_type="MARKET",
            )
            logger.info(
                "LIVE BUY %s: qty=%.8f — orderId=%s, status=%s",
                pair, quantity,
                order_result.get("orderId"),
                order_result.get("status"),
            )

            # Get the actual fill price from the order result
            fills = order_result.get("fills", [])
            if fills:
                total_cost = sum(float(f["price"]) * float(f["qty"]) for f in fills)
                total_qty = sum(float(f["qty"]) for f in fills)
                actual_price = total_cost / total_qty if total_qty > 0 else entry_price
                actual_qty = total_qty
            else:
                actual_price = entry_price
                actual_qty = quantity

            # Recalculate stop-loss based on actual fill
            stop_loss_price = actual_price * (1.0 - sl_pct / 100.0)

            # Create position
            position = Position(
                pair=pair,
                side="BUY",
                entry_price=actual_price,
                quantity=actual_qty,
                entry_time=candle.timestamp,
                stop_loss=stop_loss_price,
                take_profit_levels=tp_levels,
                entry_reason=signal.reason,
                metadata={
                    "strategy_name": signal.strategy_name,
                    "trailing_activation_pct": trailing_activation_pct,
                    "trailing_distance_pct": trailing_distance_pct,
                    "max_hold_minutes": max_hold_minutes,
                    "order_id": str(order_result.get("orderId", "")),
                    "dry_run": False,
                },
            )
            self._open_positions[pair] = position
            self._daily_trade_count += 1

            # Place stop-loss order on exchange
            try:
                tick_size = symbol_info.tick_size if symbol_info else 0.01
                sl_result = await self._exchange_rest.set_stop_loss(
                    pair=pair,
                    quantity=actual_qty,
                    stop_price=stop_loss_price,
                    tick_size=tick_size,
                )
                # Store the SL order ID so we can cancel it on exit.
                position.metadata["sl_order_id"] = str(sl_result.get("orderId", ""))
                logger.info("Stop-loss set for %s at %.2f", pair, stop_loss_price)
            except Exception as exc:
                logger.error("Failed to set stop-loss for %s: %s", pair, exc)

            # Balance is updated by _handle_balance_update via WS.
            # Do NOT subtract here to avoid double-counting.

            # Save to DB
            await self._save_trade_to_db(position, "OPEN")

            # Notify
            await self._send_notification(
                f"BUY {pair}\n"
                f"Price: {actual_price:.2f}\n"
                f"Qty: {actual_qty:.8f}\n"
                f"SL: {stop_loss_price:.2f}\n"
                f"Reason: {signal.reason}"
            )

        except Exception as exc:
            logger.error("Failed to execute BUY for %s: %s", pair, exc)

    # ------------------------------------------------------------------
    # Position exit management
    # ------------------------------------------------------------------

    async def _check_exits(self, pair: str, candle: Candle) -> None:
        """Check all open positions on this pair for exit conditions.

        Called on every closed base-TF candle. Delegates to
        PositionManager.update_position() which checks stop-loss,
        trailing stop, take-profit, and time-based exits.
        """
        if pair not in self._open_positions:
            return

        position = self._open_positions[pair]
        if not position.is_open:
            return

        current_price = candle.close
        exit_signals = self._position_manager.update_position(
            position, current_price, candle.timestamp
        )

        if exit_signals:
            # Act on the first exit signal (highest priority)
            exit_signal = exit_signals[0]
            logger.info(
                "Exit signal for %s: %s (reason: %s)",
                pair, exit_signal.type.value, exit_signal.reason,
            )
            # Partial take-profit levels (close_pct < 100) only sell part of
            # the position; everything else closes it entirely.
            pct_to_close = float((exit_signal.metadata or {}).get("pct_to_close", 100.0))
            if exit_signal.reason.startswith("TAKE_PROFIT") and 0.0 < pct_to_close < 100.0:
                await self._partial_close(position, candle, pct_to_close, exit_signal.reason)
            else:
                await self._close_position(position, candle, exit_signal.reason)

    async def _partial_close(
        self, position: Position, candle: Candle, pct_to_close: float, reason: str
    ) -> None:
        """Sell *pct_to_close* % of an open position (partial take-profit).

        The remaining quantity stays open with its stop-loss, trailing stop
        and remaining take-profit levels. Falls back to a full close when
        the remainder would be below the exchange minimums.
        """
        pair = position.pair
        exit_price = candle.close
        close_qty = position.quantity * pct_to_close / 100.0

        sym = self._symbol_info.get(pair)
        if sym and sym.step_size > 0:
            steps = math.floor(close_qty / sym.step_size)
            precision = max(0, -int(math.floor(math.log10(sym.step_size))))
            close_qty = round(steps * sym.step_size, precision)
        remaining_qty = position.quantity - close_qty
        min_notional = sym.min_notional if sym else 0.0
        min_qty = sym.min_qty if sym else 0.0
        if (
            close_qty <= 0.0
            or remaining_qty <= 0.0
            or remaining_qty * exit_price < min_notional
            or remaining_qty < min_qty
            or close_qty * exit_price < min_notional
        ):
            await self._close_position(position, candle, reason)
            return

        if self._config.dry_run:
            logger.info(
                "[DRY-RUN] PARTIAL SELL %s: qty=%.8f (%.0f%%) at %.2f (reason: %s)",
                pair, close_qty, pct_to_close, exit_price, reason,
            )
        else:
            self._pending_close.add(pair)
            # The exchange SL covers the full quantity: cancel it, sell the
            # partial quantity, then re-arm the SL on what remains.
            sl_order_id = position.metadata.get("sl_order_id")
            if sl_order_id and self._exchange_rest is not None:
                await self._exchange_rest.cancel_order(pair, sl_order_id)
            try:
                order_result = await self._exchange_rest.place_order(
                    pair=pair, side="SELL", quantity=close_qty, order_type="MARKET",
                )
                fills = order_result.get("fills", [])
                if fills:
                    total_cost = sum(float(f["price"]) * float(f["qty"]) for f in fills)
                    total_qty = sum(float(f["qty"]) for f in fills)
                    exit_price = total_cost / total_qty if total_qty > 0 else exit_price
                logger.info(
                    "LIVE PARTIAL SELL %s: qty=%.8f — orderId=%s",
                    pair, close_qty, order_result.get("orderId"),
                )
            except Exception as exc:
                logger.error("Failed to execute partial SELL for %s: %s", pair, exc)
                remaining_qty = position.quantity  # nothing sold: re-arm SL on full qty
                close_qty = 0.0
            await self._rearm_stop_loss(position, remaining_qty)
            self._pending_close.discard(pair)
            if close_qty <= 0.0:
                return

        # Record the sold part as its own closed trade.
        sold = dataclasses.replace(
            position,
            quantity=close_qty,
            exit_price=exit_price,
            exit_time=candle.timestamp,
            exit_reason=reason,
            status=PositionStatus.CLOSED,
            metadata=dict(position.metadata),
        )
        sold.update_pnl(exit_price)
        fees = 0.0
        if self._config.dry_run:
            share = close_qty / position.quantity
            entry_fee = position.metadata.get("entry_fee", 0.0)
            fees = entry_fee * share + exit_price * close_qty * self._dry_run_fee_rate
            position.metadata["entry_fee"] = entry_fee * (1.0 - share)
        trade = Trade.from_position(sold, fees=fees)
        trade.strategy_name = position.metadata.get("strategy_name", "")
        self._daily_trades.append(trade)
        self._daily_pnl_usdt += trade.pnl_usdt
        if trade.pnl_usdt < 0:
            self._last_loss_time = candle.timestamp
        if self._config.dry_run:
            self._balance += exit_price * close_qty * (1.0 - self._dry_run_fee_rate)

        position.quantity = remaining_qty
        await self._save_partial_trade_to_db(position, trade)

        await self._send_notification(
            f"{'[DRY-RUN] ' if self._config.dry_run else ''}PARTIAL SELL {pair} "
            f"({pct_to_close:.0f}%)\n"
            f"Exit: {exit_price:.2f}\n"
            f"PnL: {trade.pnl_usdt:+.2f} USDT ({trade.pnl_pct:+.2f}%)\n"
            f"Remaining: {remaining_qty:.8f}\n"
            f"Reason: {reason}"
        )

    async def _rearm_stop_loss(self, position: Position, quantity: float) -> None:
        """Place a new exchange stop-loss order for *quantity* (live mode)."""
        if self._exchange_rest is None or position.stop_loss <= 0.0 or quantity <= 0.0:
            return
        sym = self._symbol_info.get(position.pair)
        try:
            sl_result = await self._exchange_rest.set_stop_loss(
                pair=position.pair,
                quantity=quantity,
                stop_price=position.stop_loss,
                tick_size=sym.tick_size if sym else 0.01,
            )
            position.metadata["sl_order_id"] = str(sl_result.get("orderId", ""))
        except Exception as exc:
            position.metadata.pop("sl_order_id", None)
            logger.error("Failed to re-arm stop-loss for %s: %s", position.pair, exc)

    async def _update_trailing_on_tick(
        self, pair: str, price: float, timestamp: datetime
    ) -> None:
        """Update trailing stop on live (non-closed) candle ticks.

        This ensures trailing highs are updated even between closed candles.
        """
        if pair not in self._open_positions:
            return

        position = self._open_positions[pair]
        if not position.is_open or not position.trailing_active:
            return

        # Update PnL
        position.update_pnl(price)

        # Update trailing high
        if position.side == "BUY" and price > position.trailing_high:
            position.trailing_high = price

    async def _close_position(
        self, position: Position, candle: Candle, reason: str
    ) -> None:
        """Close an open position.

        Handles both dry-run (simulated) and live (market sell) modes.

        Parameters
        ----------
        position : Position
            The position to close.
        candle : Candle
            The current candle (for price/time reference).
        reason : str
            Reason for closing (e.g. "STOP_LOSS", "TRAILING_STOP",
            "TAKE_PROFIT", "STRATEGY_EXIT").
        """
        pair = position.pair
        exit_price = candle.close

        if self._config.dry_run:
            logger.info(
                "[DRY-RUN] SELL %s: qty=%.8f at %.2f (reason: %s)",
                pair, position.quantity, exit_price, reason,
            )
        else:
            # Mark pair as pending close so _handle_order_update skips it.
            self._pending_close.add(pair)

            # Cancel the exchange stop-loss order first to free locked qty.
            sl_order_id = position.metadata.get("sl_order_id")
            if sl_order_id and self._exchange_rest is not None:
                await self._exchange_rest.cancel_order(pair, sl_order_id)

            # Live mode: place market sell order.
            # Use actual Binance balance (fees may have reduced qty).
            sell_qty = position.quantity
            try:
                base_asset = pair.replace("USDT", "")
                real_balance = await self._exchange_rest.get_balance(base_asset)
                if 0 < real_balance < sell_qty:
                    logger.info(
                        "Adjusting sell qty for %s: %.8f -> %.8f (fee-adjusted)",
                        pair, sell_qty, real_balance,
                    )
                    sell_qty = real_balance
                # Clamp to symbol step_size
                sym = self._symbol_info.get(pair)
                if sym and sym.step_size > 0:
                    steps = math.floor(sell_qty / sym.step_size)
                    sell_qty = steps * sym.step_size
                    precision = max(0, -int(math.floor(math.log10(sym.step_size))))
                    sell_qty = round(sell_qty, precision)
            except Exception as exc:
                logger.warning("Could not fetch real balance for %s: %s", pair, exc)

            try:
                order_result = await self._exchange_rest.place_order(
                    pair=pair,
                    side="SELL",
                    quantity=sell_qty,
                    order_type="MARKET",
                )
                logger.info(
                    "LIVE SELL %s: qty=%.8f — orderId=%s",
                    pair, position.quantity, order_result.get("orderId"),
                )

                # Get actual fill price
                fills = order_result.get("fills", [])
                if fills:
                    total_cost = sum(float(f["price"]) * float(f["qty"]) for f in fills)
                    total_qty = sum(float(f["qty"]) for f in fills)
                    exit_price = total_cost / total_qty if total_qty > 0 else exit_price

            except Exception as exc:
                logger.error("Failed to execute SELL for %s: %s", pair, exc)
                self._pending_close.discard(pair)
                return

        # Update position
        position.exit_price = exit_price
        position.exit_time = candle.timestamp
        position.exit_reason = reason
        position.status = PositionStatus.CLOSED
        position.update_pnl(exit_price)

        # Create Trade record
        # Dry-run: simulated fees (entry + exit). Live: TODO read the
        # commissions from the exchange fills.
        fees = 0.0
        if self._config.dry_run:
            fees = position.metadata.get("entry_fee", 0.0) + exit_price * position.quantity * self._dry_run_fee_rate
        trade = Trade.from_position(position, fees=fees)
        trade.strategy_name = position.metadata.get("strategy_name", "")
        self._daily_trades.append(trade)

        # Update daily PnL
        self._daily_pnl_usdt += trade.pnl_usdt

        # Track last loss for cooldown filter
        if trade.pnl_usdt < 0:
            self._last_loss_time = candle.timestamp

        # In live mode, balance is updated by _handle_balance_update via WS.
        # Only adjust manually in dry_run.
        if self._config.dry_run:
            notional = exit_price * position.quantity
            self._balance += notional * (1.0 - self._dry_run_fee_rate)

        # Remove from open positions
        if pair in self._open_positions:
            del self._open_positions[pair]

        # Save trade to DB
        await self._save_trade_to_db(position, "CLOSED", trade)

        # Notify
        pnl_emoji = "+" if trade.pnl_usdt >= 0 else ""
        await self._send_notification(
            f"{'[DRY-RUN] ' if self._config.dry_run else ''}SELL {pair}\n"
            f"Exit: {exit_price:.2f}\n"
            f"PnL: {pnl_emoji}{trade.pnl_usdt:.2f} USDT ({pnl_emoji}{trade.pnl_pct:.2f}%)\n"
            f"Reason: {reason}"
        )

        # Release pending-close lock.
        self._pending_close.discard(pair)

        logger.info(
            "Position closed: %s, PnL=%.2f USDT (%.2f%%)",
            pair, trade.pnl_usdt, trade.pnl_pct,
        )

    # ------------------------------------------------------------------
    # User data stream handlers
    # ------------------------------------------------------------------

    async def _handle_order_update(self, data: dict[str, Any]) -> None:
        """Process an order fill or status change from user data stream.

        Updates the internal position state and records the trade
        if the order is fully filled.
        """
        order_status = data.get("X", "")  # NEW, PARTIALLY_FILLED, FILLED, CANCELED, etc.
        pair = data.get("s", "")
        side = data.get("S", "")  # BUY or SELL
        order_type = data.get("o", "")
        executed_qty = float(data.get("z", 0))
        price = float(data.get("L", 0))  # Last filled price

        logger.info(
            "Order update: %s %s %s status=%s qty=%.8f price=%.2f",
            side, pair, order_type, order_status, executed_qty, price,
        )

        if order_status == "FILLED" and pair in self._open_positions:
            # Skip if _close_position is already handling this pair.
            if pair in self._pending_close:
                logger.debug("Skipping duplicate fill for %s (pending_close)", pair)
                return

            position = self._open_positions[pair]

            # If this is a SELL fill (stop-loss or manual), close the position
            if side == "SELL" and position.is_open:
                position.exit_price = price
                position.exit_time = datetime.now(timezone.utc)
                position.exit_reason = f"ORDER_FILLED ({order_type})"
                position.status = PositionStatus.CLOSED
                position.update_pnl(price)

                trade = Trade.from_position(position)
                self._daily_trades.append(trade)
                self._daily_pnl_usdt += trade.pnl_usdt

                if trade.pnl_usdt < 0:
                    self._last_loss_time = datetime.now(timezone.utc)

                # Return capital
                self._balance += price * position.quantity

                del self._open_positions[pair]

                await self._save_trade_to_db(position, "CLOSED", trade)
                logger.info(
                    "Position closed via order fill: %s PnL=%.2f",
                    pair, trade.pnl_usdt,
                )

    async def _handle_balance_update(self, data: dict[str, Any]) -> None:
        """Process a balance update event.

        Logs the updated balances and refreshes internal state.
        """
        balances = data.get("B", [])
        for bal in balances:
            asset = bal.get("a", "")
            free = float(bal.get("f", 0))
            if asset == "USDT":
                self._balance = free
                logger.debug("Balance updated: USDT = %.2f", free)

    # ------------------------------------------------------------------
    # Trust level
    # ------------------------------------------------------------------

    def _get_trust_level(self) -> str:
        """Determine the current trust level based on recent performance.

        Returns CRAWL / WALK / RUN / SPRINT based on win rate and
        consecutive performance.
        """
        if not self._daily_trades:
            return "CRAWL"

        total = len(self._daily_trades)
        wins = sum(1 for t in self._daily_trades if t.pnl_usdt > 0)
        win_rate = (wins / total) * 100.0 if total > 0 else 0.0

        # Need minimum 5 trades to move beyond WALK
        if total < 5:
            # Cap at WALK level (max score 64) with few trades
            max_score = 64.0
        else:
            max_score = 100.0

        # Simple trust score: base on win rate + trade count bonus
        score = win_rate * 0.6  # 60% weight on win rate
        score += min(total * 2, 20)  # Up to 20 points for trade count

        # Penalty for consecutive losses
        consecutive_losses = 0
        for t in reversed(self._daily_trades):
            if t.pnl_usdt < 0:
                consecutive_losses += 1
            else:
                break
        score -= consecutive_losses * 10

        score = max(0.0, min(max_score, score))

        for name, (low, high, _frac) in TRUST_LEVELS.items():
            if low <= score < high:
                return name

        return "SPRINT" if score >= 100.0 else "CRAWL"

    # ------------------------------------------------------------------
    # Helper: daily PnL percentage
    # ------------------------------------------------------------------

    async def _roll_daily_stats(self, timestamp: datetime) -> None:
        """Reset the daily counters when a candle opens a new UTC day.

        Without this, max_daily_trades / max_daily_loss / circuit breakers
        counted every trade since the engine started and ended up blocking
        all new entries until a restart.
        """
        day = _as_utc(timestamp).date()
        if self._stats_day is None:
            self._stats_day = day
            return
        if day == self._stats_day:
            return
        # Persist the finished day before clearing it.
        await self._save_daily_stats(day=self._stats_day)
        logger.info(
            "New trading day %s: resetting daily stats (%d trades, PnL=%.2f USDT)",
            day, self._daily_trade_count, self._daily_pnl_usdt,
        )
        self._stats_day = day
        self._daily_trades = []
        self._daily_trade_count = 0
        self._daily_pnl_usdt = 0.0
        self._cb_trades_offset = 0

    def _daily_pnl_pct(self) -> float:
        """Calculate daily PnL as percentage of starting capital."""
        starting_capital = self._config.capital_per_pair * len(self._config.pairs)
        if starting_capital <= 0:
            return 0.0
        return (self._daily_pnl_usdt / starting_capital) * 100.0

    # ------------------------------------------------------------------
    # Strategy loading
    # ------------------------------------------------------------------

    async def _load_strategy(self) -> None:
        """Load the active strategy from DB or use default config."""
        # Try loading from DB
        if self._repository is not None:
            try:
                strategy_data = await self._repository.get_active_strategy()
                if strategy_data and strategy_data.get("json_definition"):
                    raw_def = strategy_data["json_definition"]
                    if isinstance(raw_def, str):
                        raw_def = json.loads(raw_def)
                    self._strategy_config = self._strategy_loader.load_from_dict(raw_def)
                    logger.info("Strategy loaded from DB: %s", self._strategy_config.name)
                    # Override engine pairs with strategy pairs if defined
                    strategy_pairs = raw_def.get("pairs")
                    if strategy_pairs and isinstance(strategy_pairs, list):
                        self._config.pairs = strategy_pairs
                        logger.info("Pairs overridden by strategy: %s", strategy_pairs)
                    self._setup_timeframe_aggregator()
                    return
            except Exception as exc:
                logger.warning("Failed to load strategy from DB: %s", exc)

        # Fallback: create a minimal strategy config from engine config
        self._strategy_config = StrategyConfig(
            name=self._config.strategy_type,
            pairs=self._config.pairs,
            timeframe=self._config.strategy_timeframe,
            risk={
                "stop_loss_pct": self._config.stop_loss_pct,
                "trailing_activation_pct": self._config.trailing_activation_pct,
                "trailing_distance_pct": self._config.trailing_distance_pct,
            },
            is_active=True,
        )
        logger.info("Using default strategy config: %s", self._strategy_config.name)
        self._setup_timeframe_aggregator()

    def _setup_timeframe_aggregator(self) -> None:
        """Configure the timeframe aggregator based on the loaded strategy.

        If the strategy timeframe equals the base timeframe (1m), no
        aggregation is needed and the aggregator is set to None.
        Otherwise, it aggregates 1m candles into the strategy timeframe.
        """
        strategy_tf = (
            self._strategy_config.timeframe
            if self._strategy_config
            else self._config.strategy_timeframe
        )
        self._effective_strategy_tf = strategy_tf
        targets = [
            tf for tf in self._strategy_timeframes()
            if tf != self._config.base_timeframe
        ]

        if not targets:
            # Strategy runs on base timeframe (e.g. 1m) -- no aggregation.
            self._timeframe_aggregator = None
            logger.info(
                "Strategy timeframe = base timeframe (%s), no aggregation needed",
                strategy_tf,
            )
        else:
            self._timeframe_aggregator = TimeframeAggregator(target_timeframes=targets)
            logger.info(
                "Timeframe aggregator configured: %s -> %s",
                self._config.base_timeframe, ", ".join(targets),
            )

    def _strategy_timeframes(self) -> list[str]:
        """Timeframes read by the strategy, strategy timeframe last."""
        if self._strategy_config is None:
            return [self._effective_strategy_tf]
        return self._strategy_loader.timeframes(self._strategy_config)

    # ------------------------------------------------------------------
    # Pair initialization
    # ------------------------------------------------------------------

    async def _initialize_pair(self, pair: str) -> None:
        """Initialize a trading pair: fetch exchange info and warm up indicators."""
        # Fetch exchange info (lot size, tick size, etc.)
        if self._exchange_rest is not None:
            try:
                info = await self._exchange_rest.get_exchange_info(pair)
                self._symbol_info[pair] = SymbolInfo(
                    min_qty=info.get("min_qty", 0.0),
                    max_qty=info.get("max_qty", float("inf")),
                    step_size=info.get("step_size", 0.0),
                    min_notional=info.get("min_notional", 0.0),
                    tick_size=info.get("tick_size", 0.01),
                )
                logger.info("Exchange info loaded for %s", pair)
            except Exception as exc:
                logger.warning("Failed to load exchange info for %s: %s", pair, exc)

        # Warm up indicators with historical candles (one fetch per timeframe)
        if self._exchange_rest is not None:
            for timeframe in self._strategy_timeframes():
                try:
                    historical = await self._exchange_rest.get_klines(
                        pair, timeframe, limit=500,
                    )
                    self._warm_up_indicators(pair, historical, timeframe)
                except Exception as exc:
                    logger.warning(
                        "Failed to warm up %s indicators for %s: %s", timeframe, pair, exc,
                    )

    # ------------------------------------------------------------------
    # Candle parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_candle(data: dict[str, Any]) -> Candle | None:
        """Parse a raw candle dict (from WS event) into a Candle model.

        Handles both the Kairos internal format and the Binance kline format.
        """
        try:
            # Check if it is already in Candle-compatible format
            if "pair" in data and "open" in data:
                ts = data.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                elif isinstance(ts, (int, float)):
                    ts = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
                elif ts is None:
                    ts = datetime.now(timezone.utc)

                return Candle(
                    timestamp=ts,
                    open=float(data["open"]),
                    high=float(data["high"]),
                    low=float(data["low"]),
                    close=float(data["close"]),
                    volume=float(data.get("volume", 0)),
                    pair=data["pair"],
                    timeframe=data.get("timeframe", "1m"),
                    is_closed=bool(data.get("is_closed", True)),
                )

            # Binance kline WS format: {"k": {...}}
            k = data.get("k")
            if k is not None:
                return Candle(
                    timestamp=datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),
                    open=float(k["o"]),
                    high=float(k["h"]),
                    low=float(k["l"]),
                    close=float(k["c"]),
                    volume=float(k["v"]),
                    pair=k.get("s", ""),
                    timeframe=k.get("i", "1m"),
                    is_closed=bool(k.get("x", False)),
                )

            return None

        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Failed to parse candle data: %s (%s)", data, exc)
            return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _restore_open_positions(self) -> None:
        """Restore open positions from the database after a restart.

        Reads all trades with status OPEN and rebuilds the in-memory
        _open_positions dict so the engine can manage them properly.
        """
        if self._repository is None:
            return

        try:
            open_trades = await self._repository.get_trades(
                filters={"status": "OPEN"}
            )
            if not open_trades:
                logger.info("No open positions to restore from DB")
                return

            for t in open_trades:
                pair = t.get("pair", "")
                if not pair or pair in self._open_positions:
                    continue

                entry_time = t.get("entry_time")
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time)
                elif entry_time is None:
                    entry_time = datetime.now(timezone.utc)

                metadata = t.get("metadata_json") or t.get("metadata") or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                position = Position(
                    pair=pair,
                    side=t.get("side", "BUY"),
                    entry_price=float(t.get("entry_price", 0)),
                    quantity=float(t.get("quantity", 0)),
                    entry_time=entry_time,
                    stop_loss=float(metadata.get("stop_loss", 0)),
                    entry_reason=t.get("entry_reason", ""),
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
                # Keep the DB row id so the exit updates this row.
                if t.get("id"):
                    position.metadata["trade_id"] = str(t["id"])

                self._open_positions[pair] = position
                logger.info(
                    "Restored position: %s qty=%.8f entry=%.2f SL=%.2f",
                    pair, position.quantity, position.entry_price,
                    position.stop_loss,
                )

            logger.info(
                "Restored %d open position(s) from DB", len(self._open_positions)
            )
        except Exception as exc:
            logger.error("Failed to restore open positions: %s", exc)

    async def _restore_daily_stats(self) -> None:
        """Restore today's daily P&L and trade count from closed trades in DB.

        This ensures the dashboard shows the correct daily P&L even after
        an engine restart.
        """
        if self._repository is None:
            return

        try:
            # DB stores naive timestamps (UTC), so use naive datetime.
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            closed_today = await self._repository.get_trades(
                filters={"status": "CLOSED", "date_from": today_start}
            )
            if not closed_today:
                return

            # Only count trades with actual exit data (skip orphan_cleanup)
            real_trades = [
                t for t in closed_today
                if t.get("exit_price") and float(t.get("exit_price", 0)) > 0
                and t.get("exit_reason", "") not in ("orphan_cleanup", "already_sold_before_restart")
            ]

            # Deduplicate by (pair, entry_time) — keep the one with exit_time
            seen: set[str] = set()
            unique_trades: list[dict] = []
            for t in real_trades:
                key = f"{t.get('pair')}_{t.get('entry_time')}"
                if key not in seen:
                    seen.add(key)
                    unique_trades.append(t)

            pnl_total = 0.0
            for t in unique_trades:
                pnl = float(t.get("pnl_usdt", 0))
                pnl_total += pnl

                # Rebuild Trade object for _daily_trades list
                entry_time = t.get("entry_time")
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time)
                exit_time = t.get("exit_time")
                if isinstance(exit_time, str):
                    exit_time = datetime.fromisoformat(exit_time)

                trade = Trade(
                    id=t.get("id", ""),
                    pair=t.get("pair", ""),
                    side=t.get("side", "BUY"),
                    entry_price=float(t.get("entry_price", 0)),
                    exit_price=float(t.get("exit_price", 0)),
                    quantity=float(t.get("quantity", 0)),
                    entry_time=entry_time,
                    exit_time=exit_time,
                    pnl_usdt=pnl,
                    pnl_pct=float(t.get("pnl_pct", 0)),
                    strategy_name=t.get("strategy_name", ""),
                    exit_reason=t.get("exit_reason", ""),
                )
                self._daily_trades.append(trade)

            self._daily_trade_count = len(unique_trades)
            self._daily_pnl_usdt = pnl_total
            logger.info(
                "Restored daily stats: %d trades, PnL=%.2f USDT",
                self._daily_trade_count, self._daily_pnl_usdt,
            )
        except Exception as exc:
            logger.error("Failed to restore daily stats: %s", exc)

    async def _save_trade_to_db(
        self,
        position: Position,
        status: str,
        trade: Trade | None = None,
    ) -> None:
        """Save a trade/position event to the database."""
        if self._repository is None:
            return

        try:
            if status == "CLOSED" and trade is not None:
                trade_id = position.metadata.get("trade_id")
                if trade_id:
                    # Close the row created at entry instead of inserting a
                    # second one: a lingering OPEN row would be restored as
                    # a ghost position at the next restart.
                    updated = await self._repository.update_trade(
                        trade_id,
                        status="CLOSED",
                        quantity=trade.quantity,
                        exit_price=trade.exit_price,
                        exit_time=_naive(trade.exit_time),
                        pnl_usdt=trade.pnl_usdt,
                        pnl_pct=trade.pnl_pct,
                        fees=trade.fees,
                        exit_reason=trade.exit_reason,
                    )
                    if updated is not None:
                        return
                await self._repository.save_trade(trade.to_dict())
            elif status == "OPEN":
                # Save as an open trade record
                trade_data = {
                    "pair": position.pair,
                    "side": position.side,
                    "entry_price": position.entry_price,
                    "quantity": position.quantity,
                    "entry_time": position.entry_time.isoformat() if position.entry_time else None,
                    "strategy_name": position.metadata.get("strategy_name", ""),
                    "entry_reason": position.entry_reason,
                    "status": "OPEN",
                    "metadata": {
                        **position.metadata,
                        "stop_loss": position.stop_loss,
                    },
                }
                trade_id = await self._repository.save_trade(trade_data)
                if trade_id:
                    position.metadata["trade_id"] = str(trade_id)
        except Exception as exc:
            logger.error("Failed to save trade to DB: %s", exc)

    async def _save_partial_trade_to_db(self, position: Position, trade: Trade) -> None:
        """Persist a partial exit: new CLOSED row + reduced qty on the open row."""
        if self._repository is None:
            return
        try:
            await self._repository.save_trade(trade.to_dict())
            trade_id = position.metadata.get("trade_id")
            if trade_id:
                await self._repository.update_trade(trade_id, quantity=position.quantity)
        except Exception as exc:
            logger.error("Failed to save partial trade to DB: %s", exc)

    async def _save_daily_stats(self, day: Any = None) -> None:
        """Calculate and save daily trading statistics (for *day*, default today)."""
        if self._repository is None:
            return

        try:
            stats = self._portfolio_manager.calculate_daily_stats(self._daily_trades)
            stats["date"] = day or self._stats_day or datetime.now(timezone.utc).date()
            stats["mode"] = self.mode
            stats["trust_level"] = self._get_trust_level()
            stats["open_positions"] = self.open_positions_count
            await self._repository.save_daily_stats(stats)
        except Exception as exc:
            logger.error("Failed to save daily stats: %s", exc)

    async def _save_state_to_cache(self) -> None:
        """Cache the current engine state to Redis for monitoring."""
        if self._cache is None:
            return

        try:
            state = {
                "status": "running" if self._running else "stopped",
                "uptime": round(self.uptime, 1),
                "pairs": self._config.pairs,
                "mode": self.mode,
                "open_positions": self.open_positions_count,
                "daily_trades": self._daily_trade_count,
                "daily_pnl_usdt": round(self._daily_pnl_usdt, 2),
                "daily_pnl_pct": round(self._daily_pnl_pct(), 2),
                "trust_level": self._get_trust_level(),
                "circuit_breaker": self._circuit_breaker_active,
                "balance": round(self._balance, 2),
                "strategy": self._strategy_config.name if self._strategy_config else "",
                "positions": {
                    pair: {
                        "entry_price": pos.entry_price,
                        "current_pnl_pct": round(pos.current_pnl_pct, 2),
                        "trailing_active": pos.trailing_active,
                    }
                    for pair, pos in self._open_positions.items()
                },
            }
            await self._cache.cache_bot_status(state)
        except Exception as exc:
            logger.warning("Failed to cache engine state: %s", exc)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def _send_notification(self, message: str) -> None:
        """Send a notification via the configured notifier."""
        if self._notifier is None:
            return

        try:
            await self._notifier.send(message)
        except Exception as exc:
            logger.warning("Failed to send notification: %s", exc)

    # ------------------------------------------------------------------
    # Public getters for health endpoint
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return a summary dict for the health endpoint."""
        positions_detail = []
        for pair, pos in self._open_positions.items():
            positions_detail.append({
                "pair": pos.pair,
                "side": pos.side,
                "entry_price": pos.entry_price,
                "quantity": pos.quantity,
                "entry_time": pos.entry_time.isoformat() if pos.entry_time else None,
                "stop_loss": pos.stop_loss,
                "pnl_pct": round(pos.current_pnl_pct, 2),
                "strategy_name": pos.metadata.get("strategy_name", ""),
            })
        return {
            "status": "running" if self._running else "stopped",
            "uptime": round(self.uptime, 1),
            "pairs": self._config.pairs,
            "open_positions": self.open_positions_count,
            "mode": self.mode,
            "daily_trades": self._daily_trade_count,
            "daily_pnl_usdt": round(self._daily_pnl_usdt, 2),
            "daily_pnl_pct": round(self._daily_pnl_pct(), 2),
            "balance": round(self._balance, 2),
            "trust_level": self._get_trust_level(),
            "circuit_breaker": self._circuit_breaker_active,
            "strategy": self._strategy_config.name if self._strategy_config else "",
            "positions": positions_detail,
        }
