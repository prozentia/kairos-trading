"""Redis cache and pub/sub adapter.

Used for:
- Caching market data (latest prices, indicator values)
- Pub/sub for real-time communication between engine and API
- Session storage and rate limiting
- Caching candles, tickers, and bot status

Dependencies: redis[hiredis] (aioredis is now part of redis-py >= 4.2)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Default TTL values (seconds)
DEFAULT_MARKET_DATA_TTL = 60
DEFAULT_CANDLE_TTL = 300
DEFAULT_TICKER_TTL = 30
DEFAULT_BOT_STATUS_TTL = 120


class RedisCache:
    """Async Redis client for caching and pub/sub.

    Parameters
    ----------
    url : str
        Redis connection URL, e.g. "redis://localhost:6379/0".
    """

    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        self._url = url
        self._client: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the Redis connection pool and test connectivity."""
        self._client = aioredis.from_url(
            self._url,
            decode_responses=True,
            encoding="utf-8",
        )
        # Test the connection
        await self._client.ping()
        logger.info("Redis connected: %s", self._url)

    async def disconnect(self) -> None:
        """Close the Redis connection pool and cancel listener tasks."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None

        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis disconnected")

    def _ensure_connected(self) -> aioredis.Redis:
        """Return the active client or raise if not connected."""
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # ------------------------------------------------------------------
    # Basic key-value operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> str | None:
        """Get a value by key.

        Parameters
        ----------
        key : str
            The cache key.

        Returns
        -------
        str | None
            The cached value, or None if the key does not exist.
        """
        client = self._ensure_connected()
        return await client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        """Set a key-value pair with optional TTL.

        Parameters
        ----------
        key : str
            The cache key.
        value : str
            The value to cache (must be a string; serialize before calling).
        ttl : int | None
            Time-to-live in seconds. None = no expiry.
        """
        client = self._ensure_connected()
        if ttl is not None:
            await client.set(key, value, ex=ttl)
        else:
            await client.set(key, value)

    async def delete(self, key: str) -> None:
        """Delete a key from the cache.

        Parameters
        ----------
        key : str
            The cache key to delete.
        """
        client = self._ensure_connected()
        await client.delete(key)

    # ------------------------------------------------------------------
    # JSON convenience methods
    # ------------------------------------------------------------------

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Get a JSON-serialized value by key.

        Parameters
        ----------
        key : str
            The cache key.

        Returns
        -------
        dict | None
            Deserialized JSON data, or None if the key does not exist.
        """
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to decode JSON for key '%s'", key)
            return None

    async def set_json(
        self,
        key: str,
        data: dict[str, Any] | list[Any],
        ttl: int | None = None,
    ) -> None:
        """Set a JSON-serializable value with optional TTL.

        Parameters
        ----------
        key : str
            The cache key.
        data : dict | list
            Data to JSON-serialize and cache.
        ttl : int | None
            Time-to-live in seconds. None = no expiry.
        """
        serialized = json.dumps(data, default=str)
        await self.set(key, serialized, ttl=ttl)

    # ------------------------------------------------------------------
    # Pub/Sub
    # ------------------------------------------------------------------

    async def publish(self, channel: str, message: str) -> None:
        """Publish a message to a Redis channel.

        Parameters
        ----------
        channel : str
            Channel name, e.g. "candles:BTCUSDT:1m", "signals".
        message : str
            Message payload (typically JSON-serialized).
        """
        client = self._ensure_connected()
        await client.publish(channel, message)
        logger.debug("Published to '%s': %s", channel, message[:100])

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[str], Awaitable[None]],
    ) -> None:
        """Subscribe to a Redis channel and invoke callback on messages.

        Creates a background task that listens for messages on the channel.
        The task runs until disconnect() is called.

        Parameters
        ----------
        channel : str
            Channel name to subscribe to.
        callback :
            Async callable invoked with each message string.
        """
        client = self._ensure_connected()
        self._pubsub = client.pubsub()
        await self._pubsub.subscribe(channel)
        logger.info("Subscribed to Redis channel: %s", channel)

        async def _listener() -> None:
            """Background loop reading messages from the pubsub."""
            try:
                async for message in self._pubsub.listen():
                    if message["type"] == "message":
                        data = message["data"]
                        try:
                            await callback(data)
                        except Exception as exc:
                            logger.error(
                                "Error in subscriber callback for '%s': %s",
                                channel, exc,
                            )
            except asyncio.CancelledError:
                logger.info(
                    "Subscription listener cancelled for '%s'", channel
                )
            except Exception as exc:
                logger.error(
                    "Subscription listener error for '%s': %s", channel, exc
                )

        self._listener_task = asyncio.create_task(_listener())

    # ------------------------------------------------------------------
    # Market data convenience methods
    # ------------------------------------------------------------------

    async def get_market_data(self, pair: str) -> dict[str, Any] | None:
        """Get cached market data for a trading pair.

        Parameters
        ----------
        pair : str
            Trading pair symbol, e.g. "BTCUSDT".

        Returns
        -------
        dict | None
            Cached market data or None if not cached.
        """
        return await self.get_json(f"market:{pair}")

    async def set_market_data(
        self,
        pair: str,
        data: dict[str, Any],
        ttl: int = DEFAULT_MARKET_DATA_TTL,
    ) -> None:
        """Cache market data for a trading pair.

        Parameters
        ----------
        pair : str
            Trading pair symbol.
        data : dict
            Market data to cache (will be JSON-serialized).
        ttl : int
            Time-to-live in seconds.
        """
        await self.set_json(f"market:{pair}", data, ttl=ttl)

    # ------------------------------------------------------------------
    # Candle caching
    # ------------------------------------------------------------------

    async def cache_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[dict[str, Any]],
        ttl: int = DEFAULT_CANDLE_TTL,
    ) -> None:
        """Cache candle data for a symbol and timeframe.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        timeframe : str
            Kline interval, e.g. "1m", "5m".
        candles : list[dict]
            List of candle dicts to cache.
        ttl : int
            Time-to-live in seconds.
        """
        key = f"candles:{symbol}:{timeframe}"
        await self.set_json(key, candles, ttl=ttl)
        logger.debug(
            "Cached %d candles for %s:%s", len(candles), symbol, timeframe
        )

    async def get_cached_candles(
        self,
        symbol: str,
        timeframe: str,
    ) -> list[dict[str, Any]] | None:
        """Get cached candle data for a symbol and timeframe.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        timeframe : str
            Kline interval, e.g. "1m", "5m".

        Returns
        -------
        list[dict] | None
            Cached candle data or None if not cached.
        """
        key = f"candles:{symbol}:{timeframe}"
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else None
        except (json.JSONDecodeError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Ticker caching
    # ------------------------------------------------------------------

    async def cache_ticker(
        self,
        symbol: str,
        price: float,
        volume: float,
        ttl: int = DEFAULT_TICKER_TTL,
    ) -> None:
        """Cache the latest ticker price and volume for a symbol.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        price : float
            Current price.
        volume : float
            24h volume.
        ttl : int
            Time-to-live in seconds.
        """
        key = f"ticker:{symbol}"
        data = {"symbol": symbol, "price": price, "volume": volume}
        await self.set_json(key, data, ttl=ttl)

    async def get_cached_ticker(
        self, symbol: str
    ) -> dict[str, Any] | None:
        """Get the cached ticker for a symbol.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".

        Returns
        -------
        dict | None
            Ticker data with 'symbol', 'price', 'volume', or None.
        """
        return await self.get_json(f"ticker:{symbol}")

    # ------------------------------------------------------------------
    # Bot status caching
    # ------------------------------------------------------------------

    async def cache_bot_status(
        self,
        status_data: dict[str, Any],
        ttl: int = DEFAULT_BOT_STATUS_TTL,
    ) -> None:
        """Cache the current bot status.

        Parameters
        ----------
        status_data : dict
            Bot status information (mode, positions, P&L, etc.).
        ttl : int
            Time-to-live in seconds.
        """
        await self.set_json("bot:status", status_data, ttl=ttl)

    async def get_bot_status(self) -> dict[str, Any] | None:
        """Get the cached bot status.

        Returns
        -------
        dict | None
            Bot status data or None if not cached.
        """
        return await self.get_json("bot:status")
