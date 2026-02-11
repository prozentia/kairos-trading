"""Telegram notification channel.

Sends formatted HTML messages to a Telegram chat using the Bot API.
Provides specialised formatters for trade, alert, and daily report messages.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}"
_SEND_TIMEOUT = 15.0


class TelegramChannel:
    """Sends notifications to Telegram chats."""

    def __init__(self, bot_token: str, default_chat_id: str = "") -> None:
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id
        self._base_url = _TELEGRAM_API.format(token=bot_token)

    # -----------------------------------------------------------------
    # Generic send
    # -----------------------------------------------------------------

    async def send(
        self,
        chat_id: str | int | None = None,
        message: str = "",
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a message to a Telegram chat.

        Returns True on success, False on failure.
        """
        target = str(chat_id) if chat_id else self.default_chat_id
        if not target:
            logger.error("No chat_id provided and no default set")
            return False

        payload = {
            "chat_id": target,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            async with httpx.AsyncClient(timeout=_SEND_TIMEOUT) as client:
                resp = await client.post(f"{self._base_url}/sendMessage", json=payload)
                resp.raise_for_status()
            return True
        except Exception:
            logger.exception("Failed to send Telegram message to %s", target)
            return False

    # -----------------------------------------------------------------
    # Trade notifications
    # -----------------------------------------------------------------

    async def send_trade_notification(self, trade_data: dict[str, Any]) -> bool:
        """Send a formatted BUY or SELL trade notification."""
        event_type = trade_data.get("type", "").upper()
        if event_type == "BUY":
            message = self._format_buy(trade_data)
        elif event_type in ("SELL", "STOP_LOSS", "TRAILING_STOP", "EMERGENCY_SELL"):
            message = self._format_sell(trade_data)
        else:
            message = f"<b>Trade Event:</b> {event_type}\n{trade_data}"

        chat_id = trade_data.get("chat_id") or self.default_chat_id
        return await self.send(chat_id, message)

    # -----------------------------------------------------------------
    # Alert notifications
    # -----------------------------------------------------------------

    async def send_alert(self, alert_data: dict[str, Any]) -> bool:
        """Send a formatted alert notification."""
        pair = alert_data.get("pair", "?")
        condition = alert_data.get("condition", "?")
        price = alert_data.get("price", 0)
        current = alert_data.get("current_price", 0)
        custom_msg = alert_data.get("message", "")

        message = (
            f"<b>🔔 Alert Triggered</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Pair:</b> {pair}\n"
            f"<b>Condition:</b> Price {condition} ${price:,.2f}\n"
            f"<b>Current:</b> ${current:,.2f}\n"
        )
        if custom_msg:
            message += f"<b>Note:</b> {custom_msg}\n"

        chat_id = alert_data.get("chat_id") or self.default_chat_id
        return await self.send(chat_id, message)

    # -----------------------------------------------------------------
    # Daily report
    # -----------------------------------------------------------------

    async def send_daily_report(self, stats: dict[str, Any]) -> bool:
        """Send a daily trading summary."""
        total_trades = stats.get("total_trades", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        win_rate = stats.get("win_rate", 0)
        pnl = stats.get("total_pnl_usdt", 0)
        pnl_pct = stats.get("total_pnl_pct", 0)
        balance = stats.get("balance", 0)

        pnl_emoji = "+" if pnl >= 0 else ""
        message = (
            f"<b>📊 Daily Report</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Trades:</b> {total_trades} ({wins}W / {losses}L)\n"
            f"<b>Win Rate:</b> {win_rate:.1f}%\n"
            f"<b>P&L:</b> {pnl_emoji}${pnl:,.2f} ({pnl_emoji}{pnl_pct:.2f}%)\n"
            f"<b>Balance:</b> ${balance:,.2f}\n"
            f"━━━━━━━━━━━━━━━\n"
        )

        # Best / worst trade
        if best := stats.get("best_trade"):
            message += f"<b>Best:</b> {best.get('pair', '?')} {best.get('pnl_pct', 0):+.2f}%\n"
        if worst := stats.get("worst_trade"):
            message += f"<b>Worst:</b> {worst.get('pair', '?')} {worst.get('pnl_pct', 0):+.2f}%\n"

        return await self.send(self.default_chat_id, message)

    # -----------------------------------------------------------------
    # Message formatters
    # -----------------------------------------------------------------

    @staticmethod
    def _format_buy(data: dict[str, Any]) -> str:
        """Format a BUY trade notification."""
        pair = data.get("pair", "?")
        price = data.get("price", 0)
        quantity = data.get("quantity", 0)
        strategy = data.get("strategy", "?")
        reason = data.get("entry_reason", data.get("reason", ""))
        capital = data.get("capital", 0)

        message = (
            f"<b>🟢 BUY Signal Executed</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Pair:</b> {pair}\n"
            f"<b>Price:</b> ${price:,.2f}\n"
            f"<b>Quantity:</b> {quantity:.6f}\n"
            f"<b>Capital:</b> ${capital:,.2f}\n"
            f"<b>Strategy:</b> {strategy}\n"
        )
        if reason:
            message += f"<b>Reason:</b> {reason}\n"
        return message

    @staticmethod
    def _format_sell(data: dict[str, Any]) -> str:
        """Format a SELL trade notification."""
        pair = data.get("pair", "?")
        event_type = data.get("type", "SELL").upper()
        entry_price = data.get("entry_price", 0)
        exit_price = data.get("exit_price", data.get("price", 0))
        pnl_usdt = data.get("pnl_usdt", 0)
        pnl_pct = data.get("pnl_pct", 0)
        reason = data.get("exit_reason", data.get("reason", event_type))
        duration = data.get("duration", "")

        pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"
        pnl_sign = "+" if pnl_pct >= 0 else ""

        message = (
            f"<b>{pnl_emoji} {event_type}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Pair:</b> {pair}\n"
            f"<b>Entry:</b> ${entry_price:,.2f}\n"
            f"<b>Exit:</b> ${exit_price:,.2f}\n"
            f"<b>P&L:</b> {pnl_sign}${pnl_usdt:,.2f} ({pnl_sign}{pnl_pct:.2f}%)\n"
            f"<b>Reason:</b> {reason}\n"
        )
        if duration:
            message += f"<b>Duration:</b> {duration}\n"
        return message
