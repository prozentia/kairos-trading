"""Kairos Trading Engine - Entry point.

Bootstraps all adapters and core components, then starts the
event-driven trading loop.  Also starts a health HTTP server for
the API layer to query.

Usage:
    python -m engine.main
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

from engine.config import EngineConfig
from engine.runner import TradingRunner
from engine.health import EngineHealthServer

logger = logging.getLogger(__name__)

# Default health server port (can be overridden via KAIROS_HEALTH_PORT)
DEFAULT_HEALTH_PORT = 8001


async def main() -> None:
    """Main entry point for the trading engine.

    Lifecycle:
    1. Load configuration from environment / config file
    2. Initialize adapters (Binance WS + REST, PostgreSQL, Redis, Telegram)
    3. Create TradingRunner with all dependencies
    4. Start the health HTTP server
    5. Start the engine and enter main event loop
    6. Handle graceful shutdown on SIGINT/SIGTERM
    """

    # -- 1. Load config ------------------------------------------------
    logger.info("Loading engine configuration...")
    config = EngineConfig.load()
    logger.info(
        "Config loaded: pairs=%s, dry_run=%s, capital_per_pair=%.2f, "
        "strategy=%s, base_tf=%s, strategy_tf=%s",
        config.pairs, config.dry_run, config.capital_per_pair,
        config.strategy_type, config.base_timeframe, config.strategy_timeframe,
    )

    # -- 2. Initialize adapters ----------------------------------------
    logger.info("Initializing adapters...")

    exchange_ws = None
    exchange_rest = None
    repository = None
    cache = None
    notifier = None

    # Exchange adapters
    if config.binance_api_key:
        try:
            from adapters.exchanges.binance_ws import BinanceWebSocket
            from adapters.exchanges.binance_rest import BinanceREST

            exchange_ws = BinanceWebSocket(
                api_key=config.binance_api_key,
                api_secret=config.binance_api_secret,
                testnet=config.testnet,
            )
            exchange_rest = BinanceREST(
                api_key=config.binance_api_key,
                api_secret=config.binance_api_secret,
                testnet=config.testnet,
            )
            logger.info("Binance adapters initialized (testnet=%s)", config.testnet)
        except ImportError as exc:
            logger.warning("Binance adapter import failed: %s", exc)
    else:
        logger.warning("No Binance API key configured, running without exchange")

    # Database
    if config.database_url:
        try:
            from adapters.database.repository import Database, PostgresRepository

            db = Database(database_url=config.database_url)
            await db.connect()
            repository = PostgresRepository(db)
            logger.info("Database connected")
        except Exception as exc:
            logger.warning("Database connection failed (non-fatal): %s", exc)

    # Cache
    if config.redis_url:
        try:
            from adapters.cache.redis import RedisCache

            cache = RedisCache(url=config.redis_url)
            # Connection is deferred to runner.start()
            logger.info("Redis cache initialized")
        except ImportError as exc:
            logger.warning("Redis adapter import failed: %s", exc)

    # Notifications (Telegram)
    if config.telegram_bot_token and config.telegram_chat_id:
        try:
            from adapters.notifications.telegram import TelegramNotifier

            notifier = TelegramNotifier(
                bot_token=config.telegram_bot_token,
                default_chat_id=config.telegram_chat_id,
            )
            await notifier.start()
            logger.info("Telegram notifier initialized and started")
        except ImportError:
            logger.warning("Telegram notifier not available")

    # -- 3. Create the trading runner ----------------------------------
    logger.info("Initializing core components...")
    runner = TradingRunner(
        config=config,
        exchange_ws=exchange_ws,
        exchange_rest=exchange_rest,
        repository=repository,
        cache=cache,
        notifier=notifier,
    )

    # -- 4. Start the health server ------------------------------------
    health_port = int(os.environ.get("KAIROS_HEALTH_PORT", DEFAULT_HEALTH_PORT))
    health_server = EngineHealthServer(
        runner=runner,
        host="0.0.0.0",
        port=health_port,
    )
    await health_server.start()

    # -- 5. Handle shutdown signals ------------------------------------
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows does not support add_signal_handler
            pass

    # -- 6. Run --------------------------------------------------------
    try:
        await runner.start()
        logger.info(
            "Engine running on port %d. Press Ctrl+C to stop.", health_port
        )
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    finally:
        logger.info("Shutting down engine...")
        await runner.stop()
        await health_server.stop()

        # Stop notifier
        if notifier is not None:
            try:
                await notifier.stop()
            except Exception:
                pass

        # Close database connection if we opened it
        if repository is not None:
            try:
                from adapters.database.repository import Database
                # The Database instance is captured by closure above
                await db.disconnect()
            except Exception:
                pass

        logger.info("Engine stopped.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main())
