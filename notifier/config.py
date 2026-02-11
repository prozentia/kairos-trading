"""Notifier configuration.

Loads settings from environment variables. Each notification channel
can be individually enabled or disabled.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NotifierConfig:
    """Configuration for the Kairos Notifier service."""

    # -- Redis (event source) ---------------------------------------------
    redis_url: str = "redis://kairos-redis:6379/0"

    # -- Telegram channel -------------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # -- Firebase Push channel --------------------------------------------
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""

    # -- Email channel (optional) -----------------------------------------
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_from: str = ""
    email_password: str = ""

    # -- Channel toggles --------------------------------------------------
    channels_enabled: dict[str, bool] = field(default_factory=lambda: {
        "telegram": True,
        "push": False,
        "email": False,
        "in_app": True,
    })

    # -- Extra ----------------------------------------------------------------
    extra: dict[str, Any] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Factory
    # -----------------------------------------------------------------

    @classmethod
    def load(cls) -> NotifierConfig:
        """Build config from environment variables."""
        config = cls(
            redis_url=os.getenv("REDIS_URL", "redis://kairos-redis:6379/0"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", ""),
            firebase_credentials_path=os.getenv("FIREBASE_CREDENTIALS_PATH", ""),
            email_smtp_host=os.getenv("EMAIL_SMTP_HOST", ""),
            email_smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
            email_from=os.getenv("EMAIL_FROM", ""),
            email_password=os.getenv("EMAIL_PASSWORD", ""),
        )

        # Parse channel toggles from env
        for channel in ("telegram", "push", "email", "in_app"):
            env_key = f"NOTIFY_{channel.upper()}_ENABLED"
            env_val = os.getenv(env_key)
            if env_val is not None:
                config.channels_enabled[channel] = env_val.lower() in ("1", "true", "yes")

        logger.info(
            "Notifier config loaded. Channels enabled: %s",
            {k: v for k, v in config.channels_enabled.items() if v},
        )
        return config
