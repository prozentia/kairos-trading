"""Health and control HTTP server for the trading engine.

Provides endpoints for the API layer (bot_manager.py) to query engine
status and send control commands.

Endpoints:
    GET  /health   -> Engine status JSON
    POST /control  -> Accept start/stop/restart commands
    GET  /logs     -> Return recent log lines

Dependencies: aiohttp
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any

from aiohttp import web

logger = logging.getLogger(__name__)

# Maximum number of log lines to keep in memory for /logs endpoint.
MAX_LOG_LINES = 500


class EngineHealthServer:
    """Lightweight HTTP server for engine health and control.

    Parameters
    ----------
    runner :
        A TradingRunner instance (or any object with a ``get_status()``
        method returning a dict).
    host : str
        Bind address (default "0.0.0.0").
    port : int
        Port to listen on (default 8001).
    """

    def __init__(
        self,
        runner: Any,
        host: str = "0.0.0.0",
        port: int = 8001,
    ) -> None:
        self._runner = runner
        self._host = host
        self._port = port
        self._app: web.Application | None = None
        self._site: web.TCPSite | None = None
        self._server_runner: web.AppRunner | None = None

        # In-memory log buffer (ring buffer)
        self._log_buffer: deque[str] = deque(maxlen=MAX_LOG_LINES)

        # Install a custom log handler that captures lines
        self._log_handler = _BufferLogHandler(self._log_buffer)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the health HTTP server."""
        self._app = web.Application()
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_post("/control", self._handle_control)
        self._app.router.add_get("/logs", self._handle_logs)

        # Attach log handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)

        self._server_runner = web.AppRunner(self._app)
        await self._server_runner.setup()
        self._site = web.TCPSite(self._server_runner, self._host, self._port)
        await self._site.start()

        logger.info(
            "Health server started on http://%s:%d", self._host, self._port
        )

    async def stop(self) -> None:
        """Stop the health HTTP server."""
        # Remove log handler
        root_logger = logging.getLogger()
        root_logger.removeHandler(self._log_handler)

        if self._server_runner is not None:
            await self._server_runner.cleanup()
            self._server_runner = None

        self._site = None
        self._app = None
        logger.info("Health server stopped")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _handle_health(self, request: web.Request) -> web.Response:
        """GET /health -- Return engine status JSON.

        Response body example::

            {
                "status": "running",
                "uptime": 123.4,
                "pairs": ["BTCUSDT"],
                "open_positions": 1,
                "mode": "dry_run",
                "daily_trades": 5,
                "daily_pnl_usdt": 12.50,
                "trust_level": "WALK",
                "circuit_breaker": false,
                "strategy": "msb_glissant"
            }
        """
        try:
            status = self._runner.get_status()
            return web.json_response(status)
        except Exception as exc:
            logger.error("Health endpoint error: %s", exc)
            return web.json_response(
                {"status": "error", "message": str(exc)},
                status=500,
            )

    async def _handle_control(self, request: web.Request) -> web.Response:
        """POST /control -- Accept engine control commands.

        Expected JSON body::

            {"command": "start" | "stop" | "restart"}

        Returns::

            {"ok": true, "command": "stop"}
        """
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"ok": False, "error": "Invalid JSON body"},
                status=400,
            )

        command = body.get("command", "").lower()

        if command == "stop":
            logger.info("Control command received: stop")
            asyncio.create_task(self._runner.stop())
            return web.json_response({"ok": True, "command": "stop"})

        elif command == "start":
            logger.info("Control command received: start")
            asyncio.create_task(self._runner.start())
            return web.json_response({"ok": True, "command": "start"})

        elif command == "restart":
            logger.info("Control command received: restart")

            async def _restart() -> None:
                await self._runner.stop()
                await asyncio.sleep(1.0)
                await self._runner.start()

            asyncio.create_task(_restart())
            return web.json_response({"ok": True, "command": "restart"})

        else:
            return web.json_response(
                {"ok": False, "error": f"Unknown command: {command!r}"},
                status=400,
            )

    async def _handle_logs(self, request: web.Request) -> web.Response:
        """GET /logs -- Return recent engine log lines.

        Query parameters:
            n (int): Number of lines to return (default 100, max 500).

        Response body::

            {"lines": ["2026-02-12 10:00:00 | INFO | ...", ...], "count": 100}
        """
        try:
            n = min(int(request.query.get("n", 100)), MAX_LOG_LINES)
        except (ValueError, TypeError):
            n = 100

        lines = list(self._log_buffer)[-n:]
        return web.json_response({"lines": lines, "count": len(lines)})


class _BufferLogHandler(logging.Handler):
    """Custom log handler that appends formatted lines to a deque."""

    def __init__(self, buffer: deque[str]) -> None:
        super().__init__()
        self._buffer = buffer
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._buffer.append(msg)
        except Exception:
            pass
