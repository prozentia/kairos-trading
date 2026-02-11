"""Trading runner -- orchestrates the main event loop.

The TradingRunner receives candle events from the exchange adapter,
updates indicators, evaluates strategies, checks risk limits, and
executes signals through the exchange adapter.

It depends on abstract interfaces (BaseExchange, BaseRepository) and
core pure-Python modules -- never on concrete adapter implementations.
"""

from __future__ import annotations

import logging
from typing import Any

from engine.config import EngineConfig

logger = logging.getLogger(__name__)


class TradingRunner:
    """Event-driven trading engine runner.

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

        # Internal state
        self._running = False
        self._positions: dict[str, Any] = {}  # pair -> Position
        self._indicator_state: dict[str, dict[str, Any]] = {}  # pair -> indicator values

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the trading engine.

        Steps:
        1. Connect all adapters (exchange, database, cache, notifier)
        2. Load exchange info for configured pairs
        3. Fetch historical candles to warm up indicators
        4. Subscribe to WebSocket streams
        5. Mark the engine as running
        """
        logger.info("Starting TradingRunner...")
        self._running = True

        # TODO: Connect adapters
        # await self._exchange_ws.connect()
        # await self._exchange_rest.connect()
        # await self._cache.connect()
        # await self._notifier.start()

        # TODO: Load pair info and warm up indicators
        # for pair in self._config.pairs:
        #     info = await self._exchange_rest.get_exchange_info(pair)
        #     historical = await self._exchange_rest.get_historical_klines(
        #         pair, self._config.timeframe, limit=200,
        #     )
        #     self._warm_up_indicators(pair, historical)

        # TODO: Subscribe to streams
        # await self._exchange_ws.subscribe_klines(
        #     self._config.pairs, self._config.timeframe, self.on_candle,
        # )
        # await self._exchange_ws.subscribe_user_data(self.on_user_data)

        logger.info("TradingRunner started for pairs: %s", self._config.pairs)

    async def stop(self) -> None:
        """Gracefully stop the trading engine.

        Steps:
        1. Mark as not running (no new signals will be processed)
        2. Cancel pending orders if any
        3. Disconnect all adapters
        """
        logger.info("Stopping TradingRunner...")
        self._running = False

        # TODO: Cancel pending orders
        # TODO: Disconnect adapters
        # await self._exchange_ws.disconnect()
        # await self._exchange_rest.disconnect()
        # await self._cache.disconnect()
        # await self._notifier.stop()

        logger.info("TradingRunner stopped.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_candle(self, candle: dict[str, Any]) -> None:
        """Handle an incoming candle event from the exchange.

        This is the main event handler that drives the trading logic.

        Pipeline:
        1. Update timeframe aggregator (e.g., build 5m from 1m candles)
        2. Update indicators for all completed timeframes
        3. Evaluate strategy conditions
        4. Apply post-signal filters (volume, time, cooldown)
        5. If signal is actionable -> check risk limits -> execute

        Parameters
        ----------
        candle : dict
            Raw candle data with keys: pair, timeframe, timestamp,
            open, high, low, close, volume, is_closed.
        """
        if not self._running:
            return

        pair = candle.get("pair", "")
        is_closed = candle.get("is_closed", False)

        # Only process closed candles for signal generation
        if not is_closed:
            # TODO: Update live price tracking / trailing stops
            return

        logger.debug("Processing closed candle for %s", pair)

        # Step 1: Update timeframe aggregator
        # aggregated = self._timeframe_aggregator.update(candle)

        # Step 2: Update indicators
        # self._update_indicators(pair, candle)

        # Step 3: Evaluate strategy
        # signal = self._evaluate_strategy(pair)

        # Step 4: Apply filters
        # if signal and signal.is_actionable:
        #     if not self._apply_filters(signal):
        #         return

        # Step 5: Risk check + execute
        #     if self._check_risk(signal):
        #         await self._execute_signal(signal)

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
    # Signal execution
    # ------------------------------------------------------------------

    async def _execute_signal(self, signal: Any) -> None:
        """Execute a trading signal by placing an order.

        Parameters
        ----------
        signal :
            A Signal object from core.models with type BUY, SELL,
            or EMERGENCY_SELL.
        """
        if self._config.dry_run:
            logger.info(
                "[DRY-RUN] Would execute %s on %s at %.2f",
                signal.type.value, signal.pair, signal.price,
            )
            # TODO: Record simulated trade in database
            return

        # TODO: Calculate position size based on risk limits
        # quantity = self._calculate_position_size(signal)

        # TODO: Place order via REST adapter
        # order_result = await self._exchange_rest.place_order(
        #     pair=signal.pair,
        #     side=signal.type.value,
        #     quantity=quantity,
        # )

        # TODO: Set stop-loss
        # TODO: Update position tracking
        # TODO: Send notification
        # TODO: Save trade to database

        logger.info("Signal execution placeholder for %s %s", signal.type, signal.pair)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    async def _handle_order_update(self, data: dict[str, Any]) -> None:
        """Process an order fill or status change.

        Updates the internal position state and records the trade
        if the order is fully filled.
        """
        order_status = data.get("X", "")
        pair = data.get("s", "")
        logger.debug("Order update for %s: status=%s", pair, order_status)

        # TODO: Update position based on fill
        # TODO: Record trade if fully filled
        # TODO: Send notification

    async def _handle_balance_update(self, data: dict[str, Any]) -> None:
        """Process a balance update event.

        Logs the updated balances for monitoring.
        """
        logger.debug("Balance update received: %s", data)
        # TODO: Update cached balances
        # TODO: Recalculate risk exposure

    # ------------------------------------------------------------------
    # Indicator and strategy helpers (to be wired to core/)
    # ------------------------------------------------------------------

    def _warm_up_indicators(self, pair: str, historical: list[dict[str, Any]]) -> None:
        """Feed historical candles into indicators to build initial state.

        Parameters
        ----------
        pair : str
            Trading pair being warmed up.
        historical : list[dict]
            Historical kline data, oldest first.
        """
        logger.info("Warming up indicators for %s with %d candles", pair, len(historical))
        # TODO: Feed each candle into the indicator registry
        # for kline in historical:
        #     candle = Candle.from_dict(kline)
        #     self._indicator_registry.update(pair, candle)
