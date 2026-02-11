"""Kairos Trading Engine - Entry point.

Bootstraps all adapters and core components, then starts the
event-driven trading loop.

Usage:
    python -m engine.main
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from engine.config import EngineConfig
from engine.runner import TradingRunner

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for the trading engine.

    Lifecycle:
    1. Load configuration from environment / config file
    2. Initialize adapters (Binance WS + REST, PostgreSQL, Redis, Telegram)
    3. Initialize core components (indicators, strategy evaluator, risk manager)
    4. Start WebSocket streams for all configured pairs
    5. Enter main event loop (runs until SIGINT/SIGTERM)
    """

    # -- 1. Load config ------------------------------------------------
    logger.info("Loading engine configuration...")
    config = EngineConfig.load()
    logger.info(
        "Config loaded: pairs=%s, dry_run=%s, capital_per_pair=%.2f",
        config.pairs, config.dry_run, config.capital_per_pair,
    )

    # -- 2. Initialize adapters ----------------------------------------
    logger.info("Initializing adapters...")

    # Exchange adapters (WebSocket for streaming, REST for orders)
    # ws_exchange = BinanceWebSocket(
    #     api_key=config.binance_api_key,
    #     api_secret=config.binance_api_secret,
    #     testnet=config.testnet,
    # )
    # rest_exchange = BinanceREST(
    #     api_key=config.binance_api_key,
    #     api_secret=config.binance_api_secret,
    #     testnet=config.testnet,
    # )

    # Database
    # repository = PostgresRepository(session_factory)

    # Cache
    # cache = RedisCache(url=config.redis_url)

    # Notifications
    # telegram = TelegramNotifier(
    #     bot_token=config.telegram_bot_token,
    #     default_chat_id=config.telegram_chat_id,
    # )

    # -- 3. Initialize core components --------------------------------
    logger.info("Initializing core components...")
    # indicators, strategy evaluator, risk manager
    # (will be wired once core/ modules are implemented)

    # -- 4. Create and start the trading runner ------------------------
    runner = TradingRunner(config=config)

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
        logger.info("Engine running. Press Ctrl+C to stop.")
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    finally:
        logger.info("Shutting down engine...")
        await runner.stop()
        logger.info("Engine stopped.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main())
