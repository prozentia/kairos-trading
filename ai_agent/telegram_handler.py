"""Telegram bot handler for the Kairos AI Agent.

Polls for incoming messages from Telegram and dispatches them to the
KairosAgent for processing. Supports slash commands and free-form chat.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ai_agent.agent import KairosAgent
from ai_agent.config import AgentConfig

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}"
_POLL_TIMEOUT = 30  # Long-polling timeout in seconds
_MAX_MESSAGE_LENGTH = 4096  # Telegram's max message size


class TelegramHandler:
    """Handles Telegram long-polling and message routing."""

    def __init__(self, agent: KairosAgent, config: AgentConfig) -> None:
        self.agent = agent
        self.config = config
        self._base_url = _TELEGRAM_API.format(token=config.telegram_bot_token)
        self._offset: int = 0

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def start_polling(self) -> None:
        """Start the long-polling loop. Blocks indefinitely."""
        logger.info("Telegram polling started (chat_id=%s)", self.config.telegram_chat_id)
        while True:
            try:
                updates = await self._get_updates()
                for update in updates:
                    await self._process_update(update)
            except asyncio.CancelledError:
                logger.info("Telegram polling cancelled")
                break
            except Exception:
                logger.exception("Error in polling loop, retrying in 5s...")
                await asyncio.sleep(5)

    # -----------------------------------------------------------------
    # Slash commands
    # -----------------------------------------------------------------

    _COMMANDS: dict[str, str] = {
        "/start": "Bienvenue sur Kairos Trading AI! Posez-moi vos questions sur le bot.",
        "/help": (
            "<b>Commandes disponibles:</b>\n"
            "/status - Etat du bot\n"
            "/stats - Statistiques 7 jours\n"
            "/portfolio - Vue du portefeuille\n"
            "/strategies - Strategies disponibles\n"
            "/alerts - Alertes actives\n"
            "/risk - Metriques de risque\n"
            "/clear - Effacer l'historique de conversation\n"
            "/help - Aide"
        ),
    }

    async def handle_command(self, chat_id: int, user_id: str, command: str) -> None:
        """Handle a slash command."""
        cmd = command.split()[0].lower()

        # Static commands
        if cmd in self._COMMANDS:
            await self._send_message(chat_id, self._COMMANDS[cmd])
            return

        # Clear history
        if cmd == "/clear":
            self.agent.clear_history(user_id)
            await self._send_message(chat_id, "Historique efface.")
            return

        # Dynamic commands -> translate to natural language for the agent
        command_to_prompt: dict[str, str] = {
            "/status": "What is the current bot status?",
            "/stats": "Show me the trading statistics for the last 7 days.",
            "/portfolio": "Show me the portfolio overview.",
            "/strategies": "List all available trading strategies.",
            "/alerts": "Show me active alerts.",
            "/risk": "Show me the current risk metrics.",
        }
        prompt = command_to_prompt.get(cmd)
        if prompt:
            await self._send_typing(chat_id)
            response = await self.agent.chat(prompt, user_id)
            await self._send_message(chat_id, self._format_response(response))
            return

        # Unknown command
        await self._send_message(chat_id, f"Commande inconnue: <code>{cmd}</code>. Tapez /help.")

    async def handle_message(self, chat_id: int, user_id: str, text: str) -> None:
        """Handle a regular text message (free-form chat)."""
        await self._send_typing(chat_id)
        response = await self.agent.chat(text, user_id)
        await self._send_message(chat_id, self._format_response(response))

    # -----------------------------------------------------------------
    # Telegram API helpers
    # -----------------------------------------------------------------

    async def _get_updates(self) -> list[dict[str, Any]]:
        """Long-poll for new updates from Telegram."""
        params = {
            "offset": self._offset,
            "timeout": _POLL_TIMEOUT,
            "allowed_updates": ["message"],
        }
        async with httpx.AsyncClient(timeout=_POLL_TIMEOUT + 10) as client:
            resp = await client.get(f"{self._base_url}/getUpdates", params=params)
            resp.raise_for_status()
            data = resp.json()

        updates = data.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return updates

    async def _send_message(self, chat_id: int, text: str) -> None:
        """Send a message to a Telegram chat. Splits long messages."""
        chunks = self._split_message(text)
        async with httpx.AsyncClient(timeout=15) as client:
            for chunk in chunks:
                payload = {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
                try:
                    resp = await client.post(f"{self._base_url}/sendMessage", json=payload)
                    resp.raise_for_status()
                except Exception:
                    logger.exception("Failed to send Telegram message to %s", chat_id)

    async def _send_typing(self, chat_id: int) -> None:
        """Send 'typing...' indicator to the chat."""
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(
                    f"{self._base_url}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                )
            except Exception:
                pass  # Non-critical, ignore errors

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    async def _process_update(self, update: dict[str, Any]) -> None:
        """Route an update to the appropriate handler."""
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        user_id = str(message["from"]["id"])
        text = message.get("text", "").strip()

        if not text:
            return

        # Access control: only respond to the configured chat
        if self.config.telegram_chat_id and str(chat_id) != self.config.telegram_chat_id:
            logger.warning("Ignoring message from unauthorized chat %s", chat_id)
            return

        if text.startswith("/"):
            await self.handle_command(chat_id, user_id, text)
        else:
            await self.handle_message(chat_id, user_id, text)

    @staticmethod
    def _format_response(text: str) -> str:
        """Format agent response for Telegram HTML.

        Escapes characters that conflict with HTML parse mode and
        converts markdown-style formatting to Telegram HTML.
        """
        # Replace markdown bold **text** with HTML <b>text</b>
        import re
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # Replace markdown inline code `text` with <code>text</code>
        text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
        return text

    @staticmethod
    def _split_message(text: str) -> list[str]:
        """Split a message into chunks that fit Telegram's size limit."""
        if len(text) <= _MAX_MESSAGE_LENGTH:
            return [text]
        chunks: list[str] = []
        while text:
            if len(text) <= _MAX_MESSAGE_LENGTH:
                chunks.append(text)
                break
            # Try to split at a newline
            split_at = text.rfind("\n", 0, _MAX_MESSAGE_LENGTH)
            if split_at == -1:
                split_at = _MAX_MESSAGE_LENGTH
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip("\n")
        return chunks
