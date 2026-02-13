"""Telegram notification adapter.

Sends trading notifications (buy/sell signals, alerts, reports) to
a Telegram chat using the Bot API.

Uses httpx for async HTTP requests.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramNotifier:
    """Send notifications to Telegram via Bot API.

    Parameters
    ----------
    bot_token : str
        Telegram Bot API token.
    default_chat_id : str
        Default chat ID to send messages to.
    """

    def __init__(self, bot_token: str, default_chat_id: str = "") -> None:
        self._bot_token = bot_token
        self._default_chat_id = default_chat_id
        self._base_url = f"{TELEGRAM_API_BASE}{bot_token}"
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialize the HTTP session."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        logger.info("TelegramNotifier started (chat_id=%s)", self._default_chat_id)

    async def stop(self) -> None:
        """Close the HTTP session."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info("TelegramNotifier stopped")

    # ------------------------------------------------------------------
    # Generic messaging
    # ------------------------------------------------------------------

    async def send(self, message: str) -> dict[str, Any]:
        """Shortcut used by the engine runner.

        Sends a plain text message to the default chat.
        """
        return await self.send_message(text=message, parse_mode="")

    async def send_message(
        self,
        chat_id: str = "",
        text: str = "",
        parse_mode: str = "HTML",
    ) -> dict[str, Any]:
        """Send a text message to a Telegram chat.

        Parameters
        ----------
        chat_id : str
            Target chat ID.  Falls back to default_chat_id if empty.
        text : str
            Message text (supports HTML or Markdown formatting).
        parse_mode : str
            "HTML" or "Markdown".  Empty string for plain text.

        Returns
        -------
        dict
            Telegram API response.
        """
        target = chat_id or self._default_chat_id
        if not target:
            logger.warning("No chat_id configured, skipping notification")
            return {"ok": False, "error": "no_chat_id"}

        if not text:
            return {"ok": False, "error": "empty_text"}

        # Create a one-shot client if start() was not called
        client = self._client or httpx.AsyncClient(timeout=15.0)
        close_after = self._client is None

        try:
            payload: dict[str, Any] = {
                "chat_id": target,
                "text": text,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode

            resp = await client.post(
                f"{self._base_url}/sendMessage",
                json=payload,
            )
            data = resp.json()

            if not data.get("ok"):
                logger.warning(
                    "Telegram sendMessage failed: %s",
                    data.get("description", "unknown error"),
                )
            return data

        except Exception as exc:
            logger.warning("Telegram request failed: %s", exc)
            return {"ok": False, "error": str(exc)}

        finally:
            if close_after:
                await client.aclose()

    # ------------------------------------------------------------------
    # Trade notifications
    # ------------------------------------------------------------------

    async def send_buy_notification(self, trade_data: dict[str, Any]) -> None:
        """Send a formatted BUY notification.

        Parameters
        ----------
        trade_data : dict
            Contains: pair, entry_price, quantity, strategy_name, entry_reason,
            stop_loss (optional).
        """
        pair = trade_data.get("pair", "???")
        price = trade_data.get("entry_price", 0)
        qty = trade_data.get("quantity", 0)
        strategy = trade_data.get("strategy_name", "")
        reason = trade_data.get("entry_reason", "")
        sl = trade_data.get("stop_loss")

        lines = [
            f"\U0001f7e2 <b>BUY {pair}</b>",
            "\u2501" * 14,
            f"Prix: <code>${price:,.2f}</code>",
            f"Quantit\u00e9: <code>{qty:.8f}</code>",
        ]
        if sl:
            lines.append(f"Stop-Loss: <code>${sl:,.2f}</code>")
        if strategy:
            lines.append(f"Strat\u00e9gie: {strategy}")
        if reason:
            lines.append(f"Raison: {reason}")

        await self.send_message(text="\n".join(lines))

    async def send_sell_notification(self, trade_data: dict[str, Any]) -> None:
        """Send a formatted SELL notification with P&L details.

        Parameters
        ----------
        trade_data : dict
            Contains: pair, entry_price, exit_price, quantity, pnl_usdt,
            pnl_pct, exit_reason, strategy_name.
        """
        pair = trade_data.get("pair", "???")
        exit_price = trade_data.get("exit_price", 0)
        pnl_usdt = trade_data.get("pnl_usdt", 0)
        pnl_pct = trade_data.get("pnl_pct", 0)
        reason = trade_data.get("exit_reason", "")

        pnl_sign = "+" if pnl_usdt >= 0 else ""
        emoji = "\U0001f7e2" if pnl_usdt >= 0 else "\U0001f534"

        lines = [
            f"{emoji} <b>SELL {pair}</b>",
            "\u2501" * 14,
            f"Prix sortie: <code>${exit_price:,.2f}</code>",
            f"PnL: <b>{pnl_sign}{pnl_usdt:.2f} USDT ({pnl_sign}{pnl_pct:.2f}%)</b>",
        ]
        if reason:
            lines.append(f"Raison: {reason}")

        await self.send_message(text="\n".join(lines))

    # ------------------------------------------------------------------
    # Alert notifications
    # ------------------------------------------------------------------

    async def send_alert(self, alert_data: dict[str, Any]) -> None:
        """Send a custom alert notification.

        Parameters
        ----------
        alert_data : dict
            Contains: type, title, body, pair (optional), price (optional).
        """
        alert_type = alert_data.get("type", "info")
        title = alert_data.get("title", "Alert")
        body = alert_data.get("body", "")

        emoji_map = {
            "warning": "\u26a0\ufe0f",
            "error": "\u274c",
            "info": "\u2139\ufe0f",
            "success": "\u2705",
        }
        emoji = emoji_map.get(alert_type, "\U0001f514")

        lines = [f"{emoji} <b>{title}</b>"]
        if body:
            lines.append(body)

        pair = alert_data.get("pair")
        price = alert_data.get("price")
        if pair:
            lines.append(f"Paire: {pair}")
        if price:
            lines.append(f"Prix: ${price:,.2f}")

        await self.send_message(text="\n".join(lines))
