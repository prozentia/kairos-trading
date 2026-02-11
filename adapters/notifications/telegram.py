"""Telegram notification adapter.

Sends trading notifications (buy/sell signals, alerts, reports) to
a Telegram chat using the Bot API.

Dependencies: aiohttp (or httpx)
"""

from __future__ import annotations

import logging
from typing import Any

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
        self._session: Any = None  # aiohttp.ClientSession

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialize the HTTP session."""
        raise NotImplementedError("TelegramNotifier.start() not yet implemented")

    async def stop(self) -> None:
        """Close the HTTP session."""
        raise NotImplementedError("TelegramNotifier.stop() not yet implemented")

    # ------------------------------------------------------------------
    # Generic messaging
    # ------------------------------------------------------------------

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
            "HTML" or "Markdown".

        Returns
        -------
        dict
            Telegram API response.
        """
        raise NotImplementedError("TelegramNotifier.send_message() not yet implemented")

    # ------------------------------------------------------------------
    # Trade notifications
    # ------------------------------------------------------------------

    async def send_buy_notification(self, trade_data: dict[str, Any]) -> None:
        """Send a formatted BUY notification.

        Parameters
        ----------
        trade_data : dict
            Contains: pair, entry_price, quantity, strategy_name, entry_reason.
        """
        raise NotImplementedError("TelegramNotifier.send_buy_notification() not yet implemented")

    async def send_sell_notification(self, trade_data: dict[str, Any]) -> None:
        """Send a formatted SELL notification with P&L details.

        Parameters
        ----------
        trade_data : dict
            Contains: pair, entry_price, exit_price, quantity, pnl_usdt,
            pnl_pct, exit_reason, strategy_name.
        """
        raise NotImplementedError("TelegramNotifier.send_sell_notification() not yet implemented")

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
        raise NotImplementedError("TelegramNotifier.send_alert() not yet implemented")
