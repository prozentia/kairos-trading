"""Binance WebSocket adapter.

Handles real-time market data and user-data streams via Binance
WebSocket API.  Manages automatic reconnection on disconnects.

Dependencies: websockets, aiohttp (for listen key REST calls)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import aiohttp
import websockets
from websockets.asyncio.client import ClientConnection

from adapters.exchanges.base import BaseExchange

logger = logging.getLogger(__name__)

# Binance WS endpoints
BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"
BINANCE_WS_COMBINED = "wss://stream.binance.com:9443/stream"
BINANCE_TESTNET_WS = "wss://testnet.binance.vision/ws"
BINANCE_TESTNET_COMBINED = "wss://testnet.binance.vision/stream"

# REST endpoints for listen key management
BINANCE_REST_BASE = "https://api.binance.com"
BINANCE_TESTNET_REST = "https://testnet.binance.vision"

# Listen key keepalive interval (30 minutes)
LISTEN_KEY_KEEPALIVE_INTERVAL = 30 * 60


class BinanceWebSocket(BaseExchange):
    """Binance WebSocket adapter for real-time streaming.

    This class manages multiple WS connections:
    - One combined stream for klines / tickers across all pairs
    - One user-data stream for fills and balance updates

    Reconnection logic is built-in: if the connection drops, the
    adapter will automatically reconnect after a short delay.
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts

        # Base URLs based on testnet flag
        if testnet:
            self._ws_base = BINANCE_TESTNET_WS
            self._ws_combined = BINANCE_TESTNET_COMBINED
            self._rest_base = BINANCE_TESTNET_REST
        else:
            self._ws_base = BINANCE_WS_BASE
            self._ws_combined = BINANCE_WS_COMBINED
            self._rest_base = BINANCE_REST_BASE

        # Active WS connections
        self._market_ws: ClientConnection | None = None
        self._user_ws: ClientConnection | None = None

        # Subscriptions registry
        self._kline_callbacks: dict[str, Callable[..., Awaitable[None]]] = {}
        self._ticker_callbacks: dict[str, Callable[..., Awaitable[None]]] = {}
        self._user_callback: Callable[..., Awaitable[None]] | None = None

        # Track active stream names for reconnection
        self._active_streams: list[str] = []

        # Background tasks for reading streams
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

        # Listen key for user-data stream
        self._listen_key: str | None = None

        # HTTP session for listen key management
        self._http_session: aiohttp.ClientSession | None = None

        # Reconnection tracking
        self._reconnect_count: dict[str, int] = {"market": 0, "user": 0}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish WebSocket connections to Binance.

        Opens the combined stream for market data.  The user-data stream
        is opened separately when subscribe_user_data() is called.
        """
        self._running = True

        # Create HTTP session for listen key REST calls
        headers = {}
        if self._api_key:
            headers["X-MBX-APIKEY"] = self._api_key
        self._http_session = aiohttp.ClientSession(headers=headers)

        logger.info(
            "BinanceWebSocket connected (testnet=%s)", self._testnet
        )

    async def disconnect(self) -> None:
        """Close all WebSocket connections and cancel background tasks."""
        self._running = False

        # Cancel all background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._tasks.clear()

        # Close market WS
        if self._market_ws is not None:
            try:
                await self._market_ws.close()
            except Exception:
                pass
            self._market_ws = None

        # Close user WS
        if self._user_ws is not None:
            try:
                await self._user_ws.close()
            except Exception:
                pass
            self._user_ws = None

        # Close HTTP session
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            self._http_session = None

        self._active_streams.clear()
        self._listen_key = None

        logger.info("BinanceWebSocket disconnected")

    # ------------------------------------------------------------------
    # Reconnection
    # ------------------------------------------------------------------

    async def _reconnect(self, stream_type: str) -> None:
        """Attempt to reconnect a dropped stream with exponential backoff.

        Parameters
        ----------
        stream_type : str
            "market" or "user" indicating which stream to reconnect.
        """
        attempt = 0
        while self._running and attempt < self._max_reconnect_attempts:
            attempt += 1
            delay = self._reconnect_delay * (2 ** (attempt - 1))
            delay = min(delay, 300.0)  # Cap at 5 minutes

            logger.warning(
                "Reconnecting %s stream (attempt %d/%d) in %.1fs...",
                stream_type, attempt, self._max_reconnect_attempts, delay,
            )
            await asyncio.sleep(delay)

            if not self._running:
                return

            try:
                if stream_type == "market" and self._active_streams:
                    await self._open_market_stream(self._active_streams)
                    self._reconnect_count["market"] = 0
                    logger.info("Market stream reconnected successfully")
                    return
                elif stream_type == "user":
                    await self._open_user_stream()
                    self._reconnect_count["user"] = 0
                    logger.info("User-data stream reconnected successfully")
                    return
            except Exception as exc:
                logger.error(
                    "Reconnection attempt %d failed for %s: %s",
                    attempt, stream_type, exc,
                )

        logger.error(
            "Failed to reconnect %s stream after %d attempts",
            stream_type, self._max_reconnect_attempts,
        )

    # ------------------------------------------------------------------
    # Market-data streams
    # ------------------------------------------------------------------

    async def subscribe_klines(
        self,
        pairs: list[str],
        timeframe: str,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Subscribe to kline streams for multiple pairs.

        Each incoming kline is parsed into a dict and passed to the callback.
        The dict contains: pair, timeframe, timestamp, open, high, low,
        close, volume, is_closed.
        """
        # Register callbacks
        for pair in pairs:
            stream_name = f"{pair.lower()}@kline_{timeframe}"
            self._kline_callbacks[stream_name] = callback
            if stream_name not in self._active_streams:
                self._active_streams.append(stream_name)

        # Open or update the combined stream
        await self._open_market_stream(self._active_streams)

    async def subscribe_ticker(
        self,
        pairs: list[str],
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Subscribe to 24h mini-ticker streams for multiple pairs."""
        for pair in pairs:
            stream_name = f"{pair.lower()}@miniTicker"
            self._ticker_callbacks[stream_name] = callback
            if stream_name not in self._active_streams:
                self._active_streams.append(stream_name)

        await self._open_market_stream(self._active_streams)

    async def subscribe_user_data(
        self,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Subscribe to the user-data stream.

        Requires a valid API key.  The adapter obtains a listen key via
        REST, opens the user-data stream, and keeps the listen key alive
        with periodic pings.
        """
        if not self._api_key:
            logger.warning("No API key, skipping user-data stream")
            return

        self._user_callback = callback
        await self._open_user_stream()

    # ------------------------------------------------------------------
    # Internal: open streams
    # ------------------------------------------------------------------

    async def _open_market_stream(self, streams: list[str]) -> None:
        """Open or reopen the combined market-data WebSocket.

        Parameters
        ----------
        streams : list[str]
            List of stream names, e.g. ["btcusdt@kline_1m", "ethusdt@kline_1m"].
        """
        # Close existing connection if any
        if self._market_ws is not None:
            try:
                await self._market_ws.close()
            except Exception:
                pass
            self._market_ws = None

        if not streams:
            return

        # Build combined stream URL
        stream_path = "/".join(streams)
        url = f"{self._ws_combined}?streams={stream_path}"

        logger.info("Opening market stream: %s", url)
        self._market_ws = await websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        )

        # Start background reader task
        task = asyncio.create_task(
            self._read_market_stream(),
            name="binance_market_reader",
        )
        self._tasks.append(task)

    async def _open_user_stream(self) -> None:
        """Open the user-data WebSocket using a listen key."""
        # Close existing
        if self._user_ws is not None:
            try:
                await self._user_ws.close()
            except Exception:
                pass
            self._user_ws = None

        # Get listen key via REST
        self._listen_key = await self._create_listen_key()
        if not self._listen_key:
            logger.error("Failed to create listen key")
            return

        url = f"{self._ws_base}/{self._listen_key}"
        logger.info("Opening user-data stream")

        self._user_ws = await websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        )

        # Start reader + keepalive tasks
        reader_task = asyncio.create_task(
            self._read_user_stream(),
            name="binance_user_reader",
        )
        keepalive_task = asyncio.create_task(
            self._keep_alive_listen_key(self._listen_key),
            name="binance_keepalive",
        )
        self._tasks.extend([reader_task, keepalive_task])

    # ------------------------------------------------------------------
    # Internal stream readers
    # ------------------------------------------------------------------

    async def _read_market_stream(self) -> None:
        """Background loop: read and dispatch market-data messages."""
        try:
            while self._running and self._market_ws is not None:
                try:
                    raw = await self._market_ws.recv()
                    data = json.loads(raw)

                    # Combined streams wrap data in {"stream": ..., "data": ...}
                    stream_name = data.get("stream", "")
                    payload = data.get("data", data)

                    await self._dispatch_market_message(stream_name, payload)

                except websockets.ConnectionClosed as exc:
                    if not self._running:
                        return
                    logger.warning(
                        "Market WS connection closed: code=%s reason=%s",
                        exc.code, exc.reason,
                    )
                    break
                except json.JSONDecodeError as exc:
                    logger.warning("Invalid JSON from market WS: %s", exc)
                except Exception as exc:
                    if not self._running:
                        return
                    logger.error("Error in market stream reader: %s", exc)
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            return

        # Attempt reconnection if still running
        if self._running:
            self._market_ws = None
            await self._reconnect("market")

    async def _read_user_stream(self) -> None:
        """Background loop: read and dispatch user-data messages."""
        try:
            while self._running and self._user_ws is not None:
                try:
                    raw = await self._user_ws.recv()
                    data = json.loads(raw)

                    if self._user_callback is not None:
                        await self._user_callback(data)

                except websockets.ConnectionClosed as exc:
                    if not self._running:
                        return
                    logger.warning(
                        "User WS connection closed: code=%s reason=%s",
                        exc.code, exc.reason,
                    )
                    break
                except json.JSONDecodeError as exc:
                    logger.warning("Invalid JSON from user WS: %s", exc)
                except Exception as exc:
                    if not self._running:
                        return
                    logger.error("Error in user stream reader: %s", exc)
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            return

        # Attempt reconnection if still running
        if self._running:
            self._user_ws = None
            await self._reconnect("user")

    async def _keep_alive_listen_key(self, listen_key: str) -> None:
        """Ping listen key every 30 minutes to keep it alive."""
        try:
            while self._running:
                await asyncio.sleep(LISTEN_KEY_KEEPALIVE_INTERVAL)
                if not self._running:
                    return
                try:
                    await self._keepalive_listen_key(listen_key)
                    logger.debug("Listen key keepalive sent")
                except Exception as exc:
                    logger.warning("Listen key keepalive failed: %s", exc)
        except asyncio.CancelledError:
            return

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    async def _dispatch_market_message(
        self, stream_name: str, payload: dict[str, Any]
    ) -> None:
        """Route a market-data message to the appropriate callback.

        Parameters
        ----------
        stream_name : str
            The stream name, e.g. "btcusdt@kline_1m".
        payload : dict
            The raw event payload from Binance.
        """
        event_type = payload.get("e", "")

        if event_type == "kline":
            # Kline event
            callback = self._kline_callbacks.get(stream_name)
            if callback is not None:
                kline_data = self._parse_kline_event(payload)
                await callback(kline_data)

        elif event_type == "24hrMiniTicker":
            # Mini-ticker event
            callback = self._ticker_callbacks.get(stream_name)
            if callback is not None:
                await callback(payload)

        else:
            # Try matching by prefix for kline callbacks
            for cb_stream, callback in self._kline_callbacks.items():
                if stream_name == cb_stream or stream_name.startswith(
                    cb_stream.split("@")[0]
                ):
                    if event_type == "kline":
                        kline_data = self._parse_kline_event(payload)
                        await callback(kline_data)
                    break

    @staticmethod
    def _parse_kline_event(payload: dict[str, Any]) -> dict[str, Any]:
        """Parse a Binance kline WS event into our standard format.

        Binance format:
        {
            "e": "kline",
            "E": 1672531200000,  # Event time
            "s": "BTCUSDT",     # Symbol
            "k": {
                "t": 1672531200000,  # Kline start time
                "T": 1672531259999,  # Kline close time
                "s": "BTCUSDT",
                "i": "1m",
                "o": "42000.00",
                "h": "42100.00",
                "l": "41900.00",
                "c": "42050.00",
                "v": "10.5",
                "x": false,  # Is this kline closed?
                ...
            }
        }

        Returns the full payload with the nested "k" dict preserved,
        since TradingRunner._parse_candle() handles the "k" format.
        """
        return payload

    # ------------------------------------------------------------------
    # Listen key REST calls
    # ------------------------------------------------------------------

    async def _create_listen_key(self) -> str | None:
        """Create a listen key via POST /api/v3/userDataStream.

        Returns
        -------
        str | None
            The listen key, or None on failure.
        """
        if self._http_session is None or self._http_session.closed:
            headers = {}
            if self._api_key:
                headers["X-MBX-APIKEY"] = self._api_key
            self._http_session = aiohttp.ClientSession(headers=headers)

        url = f"{self._rest_base}/api/v3/userDataStream"
        try:
            async with self._http_session.post(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    key = data.get("listenKey", "")
                    logger.info("Listen key created: %s...", key[:8] if key else "?")
                    return key
                else:
                    body = await resp.text()
                    logger.error(
                        "Failed to create listen key: HTTP %d — %s",
                        resp.status, body,
                    )
                    return None
        except Exception as exc:
            logger.error("Failed to create listen key: %s", exc)
            return None

    async def _keepalive_listen_key(self, listen_key: str) -> None:
        """Keepalive a listen key via PUT /api/v3/userDataStream.

        Parameters
        ----------
        listen_key : str
            The listen key to refresh.
        """
        if self._http_session is None or self._http_session.closed:
            return

        url = f"{self._rest_base}/api/v3/userDataStream"
        try:
            async with self._http_session.put(
                url, params={"listenKey": listen_key}
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "Listen key keepalive failed: HTTP %d — %s",
                        resp.status, body,
                    )
        except Exception as exc:
            logger.warning("Listen key keepalive error: %s", exc)

    # ------------------------------------------------------------------
    # REST methods (delegated to BinanceREST in production)
    # ------------------------------------------------------------------
    # These are included to satisfy the BaseExchange interface.
    # In practice, the engine should use BinanceREST for order management
    # and this class for streaming only.

    async def get_historical_klines(
        self, pair: str, timeframe: str, limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for historical klines")

    async def place_order(
        self, pair: str, side: str, quantity: float,
        order_type: str = "MARKET", price: float | None = None,
    ) -> dict[str, Any]:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for order placement")

    async def cancel_order(self, pair: str, order_id: str) -> bool:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for order cancellation")

    async def get_balance(self, asset: str) -> float:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for balance queries")

    async def get_all_balances(self) -> dict[str, float]:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for balance queries")

    async def set_stop_loss(
        self, pair: str, quantity: float, stop_price: float,
    ) -> dict[str, Any]:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for stop-loss orders")

    async def get_exchange_info(self, pair: str) -> dict[str, Any]:
        """Not implemented in WS adapter -- use BinanceREST."""
        raise NotImplementedError("Use BinanceREST for exchange info")
