"""Notification dispatcher.

Subscribes to Redis pub/sub channels for trading events and routes
notifications to the appropriate channels (Telegram, Push, Email).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from notifier.channels.email import EmailChannel
from notifier.channels.push import PushChannel
from notifier.channels.telegram import TelegramChannel
from notifier.config import NotifierConfig

logger = logging.getLogger(__name__)

# Redis pub/sub channels the notifier subscribes to
_REDIS_CHANNELS = [
    "kairos:trades",   # BUY, SELL, SL events
    "kairos:alerts",   # Alert triggers
    "kairos:system",   # Bot status changes
    "kairos:ai",       # AI report ready
]


class NotificationDispatcher:
    """Routes events from Redis pub/sub to notification channels."""

    def __init__(self, config: NotifierConfig) -> None:
        self.config = config
        self._redis: aioredis.Redis | None = None

        # Initialise channels based on config
        self.telegram: TelegramChannel | None = None
        self.push: PushChannel | None = None
        self.email: EmailChannel | None = None

        if config.channels_enabled.get("telegram") and config.telegram_bot_token:
            self.telegram = TelegramChannel(
                bot_token=config.telegram_bot_token,
                default_chat_id=config.telegram_chat_id,
            )

        if config.channels_enabled.get("push") and config.firebase_credentials_path:
            self.push = PushChannel(
                project_id=config.firebase_project_id,
                credentials_path=config.firebase_credentials_path,
            )

        if config.channels_enabled.get("email") and config.email_smtp_host:
            self.email = EmailChannel(
                smtp_host=config.email_smtp_host,
                smtp_port=config.email_smtp_port,
                from_addr=config.email_from,
                password=config.email_password,
            )

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def start(self) -> None:
        """Connect to Redis and start listening to events. Blocks indefinitely."""
        self._redis = aioredis.from_url(self.config.redis_url, decode_responses=True)
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(*_REDIS_CHANNELS)
        logger.info("Subscribed to Redis channels: %s", _REDIS_CHANNELS)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    await self.dispatch(channel, data)
                except Exception:
                    logger.exception("Error processing event: %s", message)
        finally:
            await pubsub.unsubscribe(*_REDIS_CHANNELS)
            await self._redis.aclose()

    async def dispatch(self, channel: str, data: dict[str, Any]) -> None:
        """Route an event to the appropriate handler based on the Redis channel."""
        handlers = {
            "kairos:trades": self._on_trade_event,
            "kairos:alerts": self._on_alert_event,
            "kairos:system": self._on_system_event,
            "kairos:ai":     self._on_ai_event,
        }
        handler = handlers.get(channel)
        if handler:
            await handler(data)
        else:
            logger.warning("No handler for channel: %s", channel)

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    async def _on_trade_event(self, data: dict[str, Any]) -> None:
        """Handle BUY / SELL / STOP_LOSS trade events."""
        event_type = data.get("type", "").upper()
        logger.info("Trade event: %s for %s", event_type, data.get("pair", "?"))

        if self.telegram:
            try:
                await self.telegram.send_trade_notification(data)
            except Exception:
                logger.exception("Telegram trade notification failed")

        if self.push:
            try:
                user_id = data.get("user_id", "")
                pair = data.get("pair", "")
                title = f"Trade {event_type}: {pair}"
                body = self._trade_summary(data)
                await self.push.send_to_user(user_id, title, body, data)
            except Exception:
                logger.exception("Push trade notification failed")

    async def _on_alert_event(self, data: dict[str, Any]) -> None:
        """Handle alert trigger events."""
        logger.info("Alert event: %s", data.get("message", "?"))

        if self.telegram:
            try:
                await self.telegram.send_alert(data)
            except Exception:
                logger.exception("Telegram alert notification failed")

        if self.push:
            try:
                user_id = data.get("user_id", "")
                title = f"Alert: {data.get('pair', '')}"
                body = data.get("message", "Alert triggered")
                await self.push.send_to_user(user_id, title, body, data)
            except Exception:
                logger.exception("Push alert notification failed")

    async def _on_system_event(self, data: dict[str, Any]) -> None:
        """Handle bot status change events (started, stopped, error)."""
        event = data.get("event", "unknown")
        logger.info("System event: %s", event)

        message = f"<b>System:</b> {event}"
        if details := data.get("details"):
            message += f"\n{details}"

        if self.telegram:
            try:
                await self.telegram.send(self.config.telegram_chat_id, message)
            except Exception:
                logger.exception("Telegram system notification failed")

    async def _on_ai_event(self, data: dict[str, Any]) -> None:
        """Handle AI report ready events."""
        logger.info("AI event: %s", data.get("type", "?"))

        report_type = data.get("type", "report")
        message = f"<b>AI {report_type.title()} Ready</b>\n"
        if summary := data.get("summary"):
            message += summary

        if self.telegram:
            try:
                await self.telegram.send(self.config.telegram_chat_id, message)
            except Exception:
                logger.exception("Telegram AI notification failed")

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _trade_summary(data: dict[str, Any]) -> str:
        """Build a short text summary for push notification body."""
        pair = data.get("pair", "?")
        event_type = data.get("type", "?").upper()
        price = data.get("price", 0)
        pnl = data.get("pnl_pct", None)
        text = f"{event_type} {pair} @ ${price:,.2f}"
        if pnl is not None:
            text += f" | P&L: {pnl:+.2f}%"
        return text
