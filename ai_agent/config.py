"""AI Agent configuration.

Loads settings from environment variables and/or a JSON config file.
The JSON file takes precedence over env vars for fields it provides.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default path for the config JSON (Docker volume or local)
_DEFAULT_CONFIG_PATH = "/app/config/ai_agent_config.json"

# Default system prompt sent to the LLM
_DEFAULT_SYSTEM_PROMPT = (
    "You are Kairos, an AI trading assistant for the Kairos Trading platform. "
    "You have access to tools that let you query the bot status, trade history, "
    "statistics, portfolio, market analysis, strategies, backtests, alerts, "
    "and risk metrics. "
    "Always respond in the user's language. Be concise and precise. "
    "When presenting numbers, use proper formatting (%, $, commas). "
    "Never give financial advice - only present data and analysis."
)


@dataclass
class AgentConfig:
    """Configuration for the Kairos AI Agent."""

    # -- OpenRouter -------------------------------------------------------
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4"

    # -- Telegram ---------------------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # -- Kairos API -------------------------------------------------------
    api_base_url: str = "http://kairos-api:8000"
    internal_api_token: str = ""

    # -- Conversation -----------------------------------------------------
    max_history: int = 20
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT

    # -- Extra (loaded from JSON but not typed) ---------------------------
    extra: dict[str, Any] = field(default_factory=dict)

    # -----------------------------------------------------------------
    # Factory
    # -----------------------------------------------------------------

    @classmethod
    def load(cls, config_path: str | None = None) -> AgentConfig:
        """Build config from env vars, then overlay with JSON file values.

        Priority: JSON file > env vars > defaults.
        """
        path = config_path or os.getenv("AI_AGENT_CONFIG_PATH", _DEFAULT_CONFIG_PATH)

        # Start from env vars
        config = cls(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            api_base_url=os.getenv("API_BASE_URL", "http://kairos-api:8000"),
            internal_api_token=os.getenv("INTERNAL_API_TOKEN", ""),
        )

        # Overlay with JSON if the file exists
        json_path = Path(path)
        if json_path.is_file():
            try:
                data: dict[str, Any] = json.loads(json_path.read_text(encoding="utf-8"))
                _apply_json(config, data)
                logger.info("Loaded AI Agent config from %s", json_path)
            except Exception:
                logger.exception("Failed to load config from %s", json_path)
        else:
            logger.info("No config file at %s, using env vars / defaults", json_path)

        return config

    def save(self, config_path: str | None = None) -> None:
        """Persist current config to the JSON file."""
        path = config_path or os.getenv("AI_AGENT_CONFIG_PATH", _DEFAULT_CONFIG_PATH)
        data = {
            "openrouter_api_key": self.openrouter_api_key,
            "openrouter_model": self.openrouter_model,
            "telegram_bot_token": self.telegram_bot_token,
            "telegram_chat_id": self.telegram_chat_id,
            "api_base_url": self.api_base_url,
            "internal_api_token": self.internal_api_token,
            "max_history": self.max_history,
            "system_prompt": self.system_prompt,
        }
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Saved AI Agent config to %s", path)
        except Exception:
            logger.exception("Failed to save config to %s", path)


def _apply_json(config: AgentConfig, data: dict[str, Any]) -> None:
    """Overlay *data* values onto *config*, ignoring unknown keys."""
    field_names = {f for f in config.__dataclass_fields__}
    for key, value in data.items():
        if key in field_names and value not in (None, ""):
            setattr(config, key, value)
        else:
            config.extra[key] = value
