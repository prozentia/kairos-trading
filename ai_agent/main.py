"""Kairos Trading AI Agent - Entry point.

Conversational AI assistant accessible via Telegram.
Uses OpenRouter for LLM access (400+ models).

Usage: python -m ai_agent.main
"""

import asyncio
import logging

from ai_agent.agent import KairosAgent
from ai_agent.config import AgentConfig
from ai_agent.telegram_handler import TelegramHandler

logger = logging.getLogger(__name__)


async def main():
    """Initialise the AI agent and start Telegram polling."""
    config = AgentConfig.load()
    agent = KairosAgent(config)
    telegram = TelegramHandler(agent, config)

    logger.info("Kairos AI Agent starting...")
    await telegram.start_polling()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main())
