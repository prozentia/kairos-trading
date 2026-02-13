"""Trading runner -- orchestrates the main event loop.

The TradingRunner receives candle events from the exchange adapter,
updates indicators, evaluates strategies, checks risk limits, and
executes signals through the exchange adapter.

It depends on abstract interfaces (BaseExchange, BaseRepository) and
core pure-Python modules -- never on concrete adapter implementations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
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
from core.strategy.loader import StrategyLoader
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
        self._indicator_states: dict[str, dict[str, Any]] = {}  # pair -> {indicator_key: state}
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

        # Circuit breaker state
        self._circuit_breaker_active = False
        self._circuit_breaker_reason = ""
        self._circuit_breaker_until: datetime | None = None

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

        if self._timeframe_aggregator is not None:
            # Aggregate 1m candles into higher timeframe (e.g. 5m).
            completed_candles = self._timeframe_aggregator.on_candle(candle)

            # Buffer higher-TF candles.
            for htf_candle in completed_candles:
                self._candle_buffer.add(htf_candle)

            # Process each completed higher-TF candle through the pipeline.
            for htf_candle in completed_candles:
                if htf_candle.timeframe == self._effective_strategy_tf:
                    await self._process_strategy_candle(pair, htf_candle)
        else:
            # Strategy runs on base timeframe -- process directly.
            await self._process_strategy_candle(pair, candle)

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
        if self._circuit_breaker_active:
            if self._circuit_breaker_until and datetime.now(timezone.utc) < self._circuit_breaker_until:
                logger.debug("Circuit breaker active: %s", self._circuit_breaker_reason)
                return
            else:
                self._circuit_breaker_active = False
                self._circuit_breaker_reason = ""
                self._circuit_breaker_until = None
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

        # Step 4: Apply post-signal filters
        candles_for_filter = self._candle_buffer.get_last(
            100, pair=pair, timeframe=self._config.strategy_timeframe
        )
        filter_config = self._strategy_config.filters or {}
        signal = self._signal_filter.apply_filters(signal, candles_for_filter, filter_config)

        if not signal.is_actionable:
            logger.info("Signal filtered out: %s", signal.reason)
            return

        # Legacy filter check (EMA trend, trading hours, loss cooldown, etc.)
        legacy_context = {
            "price": candle.close,
            "timestamp": candle.timestamp,
            "daily_trade_count": self._daily_trade_count,
            "daily_pnl_pct": self._daily_pnl_pct(),
            "last_loss_time": self._last_loss_time,
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
                self._daily_trades,
                self._daily_pnl_pct(),
                self._balance,
            )
            if not cb_ok:
                logger.warning("Circuit breaker tripped: %s", cb_reason)
                self._circuit_breaker_active = True
                self._circuit_breaker_reason = cb_reason
                # Pause 30 min for consecutive losses, 24h for large loss
                if "consecutive" in cb_reason.lower():
                    from datetime import timedelta
                    self._circuit_breaker_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                else:
                    from datetime import timedelta
                    self._circuit_breaker_until = datetime.now(timezone.utc) + timedelta(hours=24)
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

        for ind_key in self._strategy_config.indicators_needed:
            try:
                indicator = self._indicator_registry.get(ind_key)
            except KeyError:
                logger.warning("Indicator %r not registered, skipping", ind_key)
                continue

            prev_state = pair_states.get(ind_key)

            try:
                if prev_state is not None:
                    # Incremental update (hot path)
                    new_state = indicator.update(candle, prev_state)
                else:
                    # Full calculation over buffered candles
                    candles = self._candle_buffer.get_all(
                        pair=pair, timeframe=candle.timeframe
                    )
                    if candles:
                        new_state = indicator.calculate(candles)
                    else:
                        new_state = indicator.calculate([candle])

                pair_states[ind_key] = new_state

            except Exception as exc:
                logger.error(
                    "Indicator %r update failed for %s: %s",
                    ind_key, pair, exc,
                )

        return pair_states

    def _warm_up_indicators(self, pair: str, historical: list[Candle]) -> None:
        """Feed historical candles into indicators to build initial state.

        Parameters
        ----------
        pair : str
            Trading pair being warmed up.
        historical : list[Candle]
            Historical candle data, oldest first.
        """
        if not historical or self._strategy_config is None:
            return

        logger.info("Warming up indicators for %s with %d candles", pair, len(historical))

        if pair not in self._indicator_states:
            self._indicator_states[pair] = {}

        # Buffer all historical candles
        for c in historical:
            self._candle_buffer.add(c)

        # Calculate initial state for each indicator
        for ind_key in self._strategy_config.indicators_needed:
            try:
                indicator = self._indicator_registry.get(ind_key)
                state = indicator.calculate(historical)
                self._indicator_states[pair][ind_key] = state
            except KeyError:
                logger.warning("Indicator %r not registered, skipping warmup", ind_key)
            except Exception as exc:
                logger.error("Indicator %r warmup failed for %s: %s", ind_key, pair, exc)

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
                    "dry_run": True,
                },
            )
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
                    "order_id": str(order_result.get("orderId", "")),
                    "dry_run": False,
                },
            )
            self._open_positions[pair] = position
            self._daily_trade_count += 1

            # Place stop-loss order on exchange
            try:
                await self._exchange_rest.set_stop_loss(
                    pair=pair,
                    quantity=actual_qty,
                    stop_price=stop_loss_price,
                )
                logger.info("Stop-loss set for %s at %.2f", pair, stop_loss_price)
            except Exception as exc:
                logger.error("Failed to set stop-loss for %s: %s", pair, exc)

            # Update balance
            notional = actual_price * actual_qty
            self._balance -= notional

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
            await self._close_position(position, candle, exit_signal.reason)

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
            # Live mode: place market sell order
            try:
                order_result = await self._exchange_rest.place_order(
                    pair=pair,
                    side="SELL",
                    quantity=position.quantity,
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
                return

        # Update position
        position.exit_price = exit_price
        position.exit_time = candle.timestamp
        position.exit_reason = reason
        position.status = PositionStatus.CLOSED
        position.update_pnl(exit_price)

        # Create Trade record
        fees = 0.0  # TODO: get actual fees from exchange fills
        trade = Trade.from_position(position, fees=fees)
        trade.strategy_name = position.metadata.get("strategy_name", "")
        self._daily_trades.append(trade)

        # Update daily PnL
        self._daily_pnl_usdt += trade.pnl_usdt

        # Track last loss for cooldown filter
        if trade.pnl_usdt < 0:
            self._last_loss_time = candle.timestamp

        # Return capital
        if not self._config.dry_run:
            notional = exit_price * position.quantity
            self._balance += notional

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

        # Simple trust score: base on win rate + trade count bonus
        score = win_rate * 0.8  # 80% weight on win rate
        score += min(total * 2, 20)  # Up to 20 points for trade count

        # Penalty for consecutive losses
        consecutive_losses = 0
        for t in reversed(self._daily_trades):
            if t.pnl_usdt < 0:
                consecutive_losses += 1
            else:
                break
        score -= consecutive_losses * 10

        score = max(0.0, min(100.0, score))

        for name, (low, high, _frac) in TRUST_LEVELS.items():
            if low <= score < high:
                return name

        return "SPRINT" if score >= 100.0 else "CRAWL"

    # ------------------------------------------------------------------
    # Helper: daily PnL percentage
    # ------------------------------------------------------------------

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

        if strategy_tf == self._config.base_timeframe:
            # Strategy runs on base timeframe (e.g. 1m) -- no aggregation.
            self._timeframe_aggregator = None
            logger.info(
                "Strategy timeframe = base timeframe (%s), no aggregation needed",
                strategy_tf,
            )
        else:
            self._timeframe_aggregator = TimeframeAggregator(
                target_timeframes=[strategy_tf],
            )
            logger.info(
                "Timeframe aggregator configured: %s -> %s",
                self._config.base_timeframe, strategy_tf,
            )

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
                )
                logger.info("Exchange info loaded for %s", pair)
            except Exception as exc:
                logger.warning("Failed to load exchange info for %s: %s", pair, exc)

        # Warm up indicators with historical candles
        if self._exchange_rest is not None:
            try:
                historical = await self._exchange_rest.get_klines(
                    pair,
                    self._effective_strategy_tf,
                    limit=500,
                )
                self._warm_up_indicators(pair, historical)
            except Exception as exc:
                logger.warning("Failed to warm up indicators for %s: %s", pair, exc)

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
                    "metadata": position.metadata,
                }
                await self._repository.save_trade(trade_data)
        except Exception as exc:
            logger.error("Failed to save trade to DB: %s", exc)

    async def _save_daily_stats(self) -> None:
        """Calculate and save daily trading statistics."""
        if self._repository is None:
            return

        try:
            stats = self._portfolio_manager.calculate_daily_stats(self._daily_trades)
            stats["date"] = datetime.now(timezone.utc).date()
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
        return {
            "status": "running" if self._running else "stopped",
            "uptime": round(self.uptime, 1),
            "pairs": self._config.pairs,
            "open_positions": self.open_positions_count,
            "mode": self.mode,
            "daily_trades": self._daily_trade_count,
            "daily_pnl_usdt": round(self._daily_pnl_usdt, 2),
            "trust_level": self._get_trust_level(),
            "circuit_breaker": self._circuit_breaker_active,
            "strategy": self._strategy_config.name if self._strategy_config else "",
        }
