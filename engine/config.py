"""Engine configuration.

Loads settings from environment variables and/or a config file.
All settings have sensible defaults for development.

Usage:
    config = EngineConfig.load()
    config = EngineConfig.from_dict({...})
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Default config file path
DEFAULT_CONFIG_PATH = "/app/config/engine_config.json"


@dataclass
class EngineConfig:
    """Trading engine configuration.

    All settings can be overridden via environment variables
    (prefixed with KAIROS_) or a JSON config file.
    """

    # -- Trading pairs -------------------------------------------------
    pairs: list[str] = field(default_factory=lambda: ["BTCUSDT"])

    # -- Mode ----------------------------------------------------------
    dry_run: bool = True
    testnet: bool = False

    # -- Capital -------------------------------------------------------
    capital_per_pair: float = 100.0
    use_full_balance: bool = False

    # -- Timeframes ----------------------------------------------------
    base_timeframe: str = "1m"
    strategy_timeframe: str = "5m"

    # -- Strategy defaults ---------------------------------------------
    strategy_type: str = "msb_glissant"
    stop_loss_pct: float = 1.5
    trailing_activation_pct: float = 0.6
    trailing_distance_pct: float = 0.3

    # -- Risk limits ---------------------------------------------------
    max_positions: int = 3
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 15.0
    max_daily_trades: int = 20

    # -- Binance credentials -------------------------------------------
    binance_api_key: str = ""
    binance_api_secret: str = ""

    # -- Database ------------------------------------------------------
    database_url: str = "postgresql+asyncpg://kairos:kairos@localhost:5432/kairos"

    # -- Redis ---------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # -- Telegram ------------------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # -- Logging -------------------------------------------------------
    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, config_path: str | None = None) -> EngineConfig:
        """Load configuration from file + environment variables.

        Priority (highest wins):
        1. Environment variables (KAIROS_<FIELD_NAME>)
        2. Config file (JSON)
        3. Defaults defined above

        Parameters
        ----------
        config_path : str | None
            Path to a JSON config file.  If None, uses
            DEFAULT_CONFIG_PATH if it exists.

        Returns
        -------
        EngineConfig
            Populated configuration instance.
        """
        data: dict[str, Any] = {}

        # Load from file if available
        path = config_path or DEFAULT_CONFIG_PATH
        if Path(path).is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Override with environment variables
        env_mapping: dict[str, str] = {
            "KAIROS_PAIRS": "pairs",
            "KAIROS_DRY_RUN": "dry_run",
            "KAIROS_TESTNET": "testnet",
            "KAIROS_CAPITAL_PER_PAIR": "capital_per_pair",
            "KAIROS_USE_FULL_BALANCE": "use_full_balance",
            "KAIROS_BASE_TIMEFRAME": "base_timeframe",
            "KAIROS_STRATEGY_TIMEFRAME": "strategy_timeframe",
            "KAIROS_TIMEFRAME": "strategy_timeframe",
            "KAIROS_STRATEGY_TYPE": "strategy_type",
            "KAIROS_STOP_LOSS_PCT": "stop_loss_pct",
            "KAIROS_TRAILING_ACTIVATION_PCT": "trailing_activation_pct",
            "KAIROS_TRAILING_DISTANCE_PCT": "trailing_distance_pct",
            "KAIROS_MAX_POSITIONS": "max_positions",
            "KAIROS_MAX_DAILY_LOSS_PCT": "max_daily_loss_pct",
            "KAIROS_MAX_DRAWDOWN_PCT": "max_drawdown_pct",
            "KAIROS_MAX_DAILY_TRADES": "max_daily_trades",
            "KAIROS_BINANCE_API_KEY": "binance_api_key",
            "KAIROS_BINANCE_API_SECRET": "binance_api_secret",
            "KAIROS_DATABASE_URL": "database_url",
            "KAIROS_REDIS_URL": "redis_url",
            "KAIROS_TELEGRAM_BOT_TOKEN": "telegram_bot_token",
            "KAIROS_TELEGRAM_CHAT_ID": "telegram_chat_id",
            "KAIROS_LOG_LEVEL": "log_level",
        }

        for env_var, field_name in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                data[field_name] = _parse_env_value(field_name, value)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineConfig:
        """Create an EngineConfig from a dictionary.

        Only known fields are used; unknown keys are ignored.

        Parameters
        ----------
        data : dict
            Configuration data.

        Returns
        -------
        EngineConfig
            Populated configuration instance.
        """
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a dictionary (excludes secrets)."""
        from dataclasses import asdict
        data = asdict(self)
        # Mask secrets
        if data.get("binance_api_key"):
            data["binance_api_key"] = "***"
        if data.get("binance_api_secret"):
            data["binance_api_secret"] = "***"
        if data.get("telegram_bot_token"):
            data["telegram_bot_token"] = "***"
        return data


def _parse_env_value(field_name: str, value: str) -> Any:
    """Parse an environment variable string into the appropriate type.

    Parameters
    ----------
    field_name : str
        The config field name (used to infer type).
    value : str
        Raw environment variable value.

    Returns
    -------
    Any
        Parsed value.
    """
    # Boolean fields
    bool_fields = {"dry_run", "testnet", "use_full_balance"}
    if field_name in bool_fields:
        return value.lower() in ("true", "1", "yes")

    # Float fields
    float_fields = {
        "capital_per_pair", "stop_loss_pct", "trailing_activation_pct",
        "trailing_distance_pct", "max_daily_loss_pct", "max_drawdown_pct",
    }
    if field_name in float_fields:
        return float(value)

    # Int fields
    int_fields = {"max_positions", "max_daily_trades"}
    if field_name in int_fields:
        return int(value)

    # List fields (comma-separated)
    if field_name == "pairs":
        return [p.strip() for p in value.split(",") if p.strip()]

    # Default: string
    return value
