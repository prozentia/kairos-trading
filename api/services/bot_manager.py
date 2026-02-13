"""Bot manager service - controls the trading engine.

The bot manager communicates with the trading engine either via:
  1. Docker API (when the engine runs in a separate container)
  2. Direct process management (when running locally)
  3. HTTP health endpoint (to check if the engine is running)

For the initial implementation, we use a file-based config and
subprocess-like control, which can be upgraded to Docker SDK later.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx


class BotManager:
    """Manages the trading engine lifecycle and configuration."""

    # Path to the bot config file (shared volume in Docker)
    CONFIG_PATH: str = os.getenv(
        "BOT_CONFIG_PATH",
        "/app/config/bot_config.json",
    )

    # Engine health endpoint (when running in Docker)
    ENGINE_HEALTH_URL: str = os.getenv(
        "ENGINE_HEALTH_URL",
        "http://kairos-engine:8001/health",
    )

    ENGINE_CONTROL_URL: str = os.getenv(
        "ENGINE_CONTROL_URL",
        "http://kairos-engine:8001",
    )

    def __init__(self) -> None:
        self._start_time: float | None = None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_status(self) -> dict[str, Any]:
        """Return current engine status.

        Attempts to query the engine's health endpoint.  Falls back to
        a default "not running" response if unreachable.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self.ENGINE_HEALTH_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "running": data.get("status") == "running",
                        "uptime_seconds": int(data.get("uptime", 0)),
                        "pairs_active": data.get("pairs", []),
                        "open_positions": data.get("open_positions", 0),
                        "last_signal_time": data.get("last_signal_time"),
                        "mode": data.get("mode", "dry_run"),
                        "version": data.get("version", "1.0.0"),
                        "strategy": data.get("strategy", ""),
                        "daily_trades": data.get("daily_trades", 0),
                        "daily_pnl_usdt": data.get("daily_pnl_usdt", 0.0),
                        "trust_level": data.get("trust_level", "CRAWL"),
                        "circuit_breaker": data.get("circuit_breaker", False),
                    }
        except Exception:
            pass

        return {
            "running": False,
            "uptime_seconds": 0,
            "pairs_active": [],
            "open_positions": 0,
            "last_signal_time": None,
            "mode": "dry_run",
            "version": "1.0.0",
            "strategy": "",
            "daily_trades": 0,
            "daily_pnl_usdt": 0.0,
            "trust_level": "CRAWL",
            "circuit_breaker": False,
        }

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    async def start(self) -> dict[str, Any]:
        """Start the engine.

        Sends a start command to the engine's control endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.ENGINE_CONTROL_URL}/start")
                if resp.status_code == 200:
                    self._start_time = time.monotonic()
                    return {"success": True, "message": "Bot started"}
                return {"success": False, "message": f"Engine responded with {resp.status_code}"}
        except Exception as exc:
            return {"success": False, "message": f"Cannot reach engine: {exc}"}

    async def stop(self) -> dict[str, Any]:
        """Stop the engine gracefully."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.ENGINE_CONTROL_URL}/stop")
                if resp.status_code == 200:
                    self._start_time = None
                    return {"success": True, "message": "Bot stopped"}
                return {"success": False, "message": f"Engine responded with {resp.status_code}"}
        except Exception as exc:
            return {"success": False, "message": f"Cannot reach engine: {exc}"}

    async def restart(self) -> dict[str, Any]:
        """Restart the engine."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{self.ENGINE_CONTROL_URL}/restart")
                if resp.status_code == 200:
                    self._start_time = time.monotonic()
                    return {"success": True, "message": "Bot restarted"}
                return {"success": False, "message": f"Engine responded with {resp.status_code}"}
        except Exception as exc:
            return {"success": False, "message": f"Cannot reach engine: {exc}"}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def get_config(self) -> dict[str, Any]:
        """Read current bot configuration from the shared config file."""
        config_path = Path(self.CONFIG_PATH)
        if not config_path.exists():
            return self._default_config()

        try:
            raw = config_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (json.JSONDecodeError, OSError):
            return self._default_config()

    async def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update bot configuration (merge with existing).

        Returns the new full config.
        """
        current = await self.get_config()

        # Merge non-None values
        for key, value in updates.items():
            if value is not None:
                current[key] = value

        # Write back
        config_path = Path(self.CONFIG_PATH)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(current, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # In Docker the volume might not be writable from API

        return current

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    async def get_logs(self, lines: int = 100, level: str | None = None) -> list[str]:
        """Read last N lines from the engine logs.

        Tries the engine's log endpoint first, then falls back to
        reading from a log file.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params: dict[str, Any] = {"lines": lines}
                if level:
                    params["level"] = level
                resp = await client.get(
                    f"{self.ENGINE_CONTROL_URL}/logs",
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("lines", [])
        except Exception:
            pass

        # Fallback: try reading from log file
        log_path = Path("/app/logs/engine.log")
        if log_path.exists():
            try:
                all_lines = log_path.read_text(encoding="utf-8").splitlines()
                if level:
                    all_lines = [ln for ln in all_lines if f"[{level.upper()}]" in ln]
                return all_lines[-lines:]
            except OSError:
                pass

        return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_config() -> dict[str, Any]:
        """Return default bot configuration."""
        return {
            "dry_run": True,
            "pairs": ["BTCUSDT"],
            "strategy_type": "",
            "ha_timeframe": "5m",
            "entry_timeframe": "1m",
            "stop_loss_pct": 1.5,
            "trailing_activation_pct": 0.6,
            "trailing_distance_pct": 0.3,
            "use_full_balance": True,
            "trade_capital_usdt": 100.0,
            "telegram_enabled": True,
        }
