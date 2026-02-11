"""Kairos Trading Notifier - Entry point.

Listens to Redis pub/sub for events and dispatches notifications
across configured channels (Telegram, Push, Email, In-App).

Usage: python -m notifier.main
"""

import asyncio
import logging

from notifier.config import NotifierConfig
from notifier.dispatcher import NotificationDispatcher

logger = logging.getLogger(__name__)


async def main():
    """Initialise the notifier and start listening to Redis events."""
    config = NotifierConfig.load()
    dispatcher = NotificationDispatcher(config)

    logger.info("Kairos Notifier starting...")
    await dispatcher.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main())
