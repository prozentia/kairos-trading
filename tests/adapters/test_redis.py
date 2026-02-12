"""Unit tests for the RedisCache adapter.

All Redis calls are mocked using unittest.mock. No real Redis instance
is needed for these tests.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio

from adapters.cache.redis import RedisCache


# ======================================================================
# Mock Redis client
# ======================================================================

class MockRedis:
    """A mock async Redis client that stores data in memory."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(
        self, key: str, value: str, ex: int | None = None
    ) -> None:
        self._data[key] = value
        if ex is not None:
            self._ttls[key] = ex

    async def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            self._ttls.pop(key, None)
            return 1
        return 0

    async def publish(self, channel: str, message: str) -> int:
        return 1

    def pubsub(self) -> MockPubSub:
        return MockPubSub()

    async def close(self) -> None:
        pass


class MockPubSub:
    """A mock async Redis PubSub."""

    def __init__(self) -> None:
        self._channels: list[str] = []

    async def subscribe(self, channel: str) -> None:
        self._channels.append(channel)

    async def close(self) -> None:
        pass

    async def listen(self):
        """Yield nothing (tests don't need to actually listen)."""
        return
        yield  # make it an async generator


# ======================================================================
# Fixtures
# ======================================================================

@pytest_asyncio.fixture
async def cache() -> RedisCache:
    """Create a RedisCache with a mock client."""
    rc = RedisCache(url="redis://localhost:6379/0")
    rc._client = MockRedis()
    return rc


# ======================================================================
# Tests: Lifecycle
# ======================================================================

class TestLifecycle:
    """Test connection lifecycle."""

    def test_init_stores_url(self) -> None:
        """Constructor should store the URL."""
        rc = RedisCache(url="redis://custom:6380/1")
        assert rc._url == "redis://custom:6380/1"
        assert rc._client is None

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """connect should create a client and test connectivity."""
        with patch(
            "adapters.cache.redis.aioredis.from_url"
        ) as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_client

            rc = RedisCache(url="redis://localhost:6379/0")
            await rc.connect()

            mock_from_url.assert_called_once()
            mock_client.ping.assert_called_once()
            assert rc._client is not None

    @pytest.mark.asyncio
    async def test_disconnect(self, cache: RedisCache) -> None:
        """disconnect should close the client."""
        await cache.disconnect()
        assert cache._client is None

    @pytest.mark.asyncio
    async def test_ensure_connected_raises(self) -> None:
        """_ensure_connected should raise when not connected."""
        rc = RedisCache()
        with pytest.raises(RuntimeError, match="not connected"):
            rc._ensure_connected()


# ======================================================================
# Tests: Basic key-value operations
# ======================================================================

class TestBasicOperations:
    """Test get, set, and delete operations."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: RedisCache) -> None:
        """set then get should return the stored value."""
        await cache.set("key1", "value1")

        result = await cache.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache: RedisCache) -> None:
        """get on a missing key should return None."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache: RedisCache) -> None:
        """set with TTL should store the TTL."""
        await cache.set("ttl_key", "ttl_value", ttl=60)

        result = await cache.get("ttl_key")
        assert result == "ttl_value"
        # Verify TTL was set on the mock
        assert cache._client._ttls.get("ttl_key") == 60

    @pytest.mark.asyncio
    async def test_delete(self, cache: RedisCache) -> None:
        """delete should remove the key."""
        await cache.set("to_delete", "value")
        assert await cache.get("to_delete") == "value"

        await cache.delete("to_delete")

        assert await cache.get("to_delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache: RedisCache) -> None:
        """delete on a missing key should not raise."""
        await cache.delete("nonexistent")  # Should not raise


# ======================================================================
# Tests: JSON operations
# ======================================================================

class TestJSONOperations:
    """Test JSON serialization convenience methods."""

    @pytest.mark.asyncio
    async def test_set_json_and_get_json(self, cache: RedisCache) -> None:
        """set_json and get_json should round-trip a dict."""
        data = {"price": 45000.0, "volume": 100.5, "pair": "BTCUSDT"}

        await cache.set_json("json_key", data)
        result = await cache.get_json("json_key")

        assert result == data

    @pytest.mark.asyncio
    async def test_get_json_missing(self, cache: RedisCache) -> None:
        """get_json on a missing key should return None."""
        result = await cache.get_json("missing_json")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, cache: RedisCache) -> None:
        """get_json with invalid JSON should return None."""
        await cache.set("bad_json", "not valid json{{{")

        result = await cache.get_json("bad_json")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_json_with_ttl(self, cache: RedisCache) -> None:
        """set_json with TTL should propagate to underlying set."""
        await cache.set_json("json_ttl", {"key": "value"}, ttl=120)

        assert cache._client._ttls.get("json_ttl") == 120

    @pytest.mark.asyncio
    async def test_set_json_list(self, cache: RedisCache) -> None:
        """set_json should handle lists."""
        data = [{"a": 1}, {"b": 2}]
        await cache.set_json("list_key", data)
        result = await cache.get_json("list_key")
        assert result == data


# ======================================================================
# Tests: Pub/Sub
# ======================================================================

class TestPubSub:
    """Test publish and subscribe operations."""

    @pytest.mark.asyncio
    async def test_publish(self, cache: RedisCache) -> None:
        """publish should call the client's publish method."""
        # The MockRedis.publish just returns 1
        await cache.publish("test_channel", "test_message")
        # No error = success

    @pytest.mark.asyncio
    async def test_subscribe(self, cache: RedisCache) -> None:
        """subscribe should create a pubsub and register the callback."""
        callback = AsyncMock()

        await cache.subscribe("signals", callback)

        assert cache._pubsub is not None
        assert cache._listener_task is not None

        # Clean up
        cache._listener_task.cancel()
        try:
            await cache._listener_task
        except asyncio.CancelledError:
            pass


# ======================================================================
# Tests: Market data convenience
# ======================================================================

class TestMarketData:
    """Test market data caching methods."""

    @pytest.mark.asyncio
    async def test_set_and_get_market_data(
        self, cache: RedisCache
    ) -> None:
        """set_market_data and get_market_data should round-trip."""
        data = {"price": 45000.0, "volume": 500.0, "rsi": 55.3}

        await cache.set_market_data("BTCUSDT", data)
        result = await cache.get_market_data("BTCUSDT")

        assert result == data

    @pytest.mark.asyncio
    async def test_get_market_data_missing(
        self, cache: RedisCache
    ) -> None:
        """get_market_data for unknown pair should return None."""
        result = await cache.get_market_data("XYZUSDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_market_data_uses_correct_key(
        self, cache: RedisCache
    ) -> None:
        """Market data should be stored under 'market:<pair>'."""
        await cache.set_market_data("ETHUSDT", {"price": 2500.0})

        raw = await cache.get("market:ETHUSDT")
        assert raw is not None
        parsed = json.loads(raw)
        assert parsed["price"] == 2500.0


# ======================================================================
# Tests: Candle caching
# ======================================================================

class TestCandleCaching:
    """Test candle data caching."""

    @pytest.mark.asyncio
    async def test_cache_and_get_candles(
        self, cache: RedisCache
    ) -> None:
        """cache_candles and get_cached_candles should round-trip."""
        candles = [
            {
                "timestamp": "2024-01-15T10:00:00",
                "open": 45000.0,
                "high": 45500.0,
                "low": 44800.0,
                "close": 45200.0,
                "volume": 100.5,
            },
            {
                "timestamp": "2024-01-15T10:05:00",
                "open": 45200.0,
                "high": 45600.0,
                "low": 45100.0,
                "close": 45400.0,
                "volume": 80.3,
            },
        ]

        await cache.cache_candles("BTCUSDT", "5m", candles)
        result = await cache.get_cached_candles("BTCUSDT", "5m")

        assert result is not None
        assert len(result) == 2
        assert result[0]["open"] == 45000.0

    @pytest.mark.asyncio
    async def test_get_cached_candles_missing(
        self, cache: RedisCache
    ) -> None:
        """get_cached_candles for uncached data should return None."""
        result = await cache.get_cached_candles("BTCUSDT", "1h")
        assert result is None

    @pytest.mark.asyncio
    async def test_candles_key_format(self, cache: RedisCache) -> None:
        """Candles should be stored under 'candles:<symbol>:<timeframe>'."""
        await cache.cache_candles("ETHUSDT", "1m", [{"test": True}])

        raw = await cache.get("candles:ETHUSDT:1m")
        assert raw is not None


# ======================================================================
# Tests: Ticker caching
# ======================================================================

class TestTickerCaching:
    """Test ticker data caching."""

    @pytest.mark.asyncio
    async def test_cache_and_get_ticker(
        self, cache: RedisCache
    ) -> None:
        """cache_ticker and get_cached_ticker should round-trip."""
        await cache.cache_ticker("BTCUSDT", 45000.0, 500.0)

        result = await cache.get_cached_ticker("BTCUSDT")

        assert result is not None
        assert result["symbol"] == "BTCUSDT"
        assert result["price"] == 45000.0
        assert result["volume"] == 500.0

    @pytest.mark.asyncio
    async def test_get_cached_ticker_missing(
        self, cache: RedisCache
    ) -> None:
        """get_cached_ticker for unknown symbol should return None."""
        result = await cache.get_cached_ticker("XYZUSDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_ticker_key_format(self, cache: RedisCache) -> None:
        """Ticker should be stored under 'ticker:<symbol>'."""
        await cache.cache_ticker("BTCUSDT", 45000.0, 500.0)

        raw = await cache.get("ticker:BTCUSDT")
        assert raw is not None


# ======================================================================
# Tests: Bot status caching
# ======================================================================

class TestBotStatusCaching:
    """Test bot status caching."""

    @pytest.mark.asyncio
    async def test_cache_and_get_bot_status(
        self, cache: RedisCache
    ) -> None:
        """cache_bot_status and get_bot_status should round-trip."""
        status = {
            "mode": "dry_run",
            "open_positions": 1,
            "daily_pnl": 12.5,
            "trust_score": 55.0,
        }

        await cache.cache_bot_status(status)
        result = await cache.get_bot_status()

        assert result is not None
        assert result["mode"] == "dry_run"
        assert result["daily_pnl"] == 12.5

    @pytest.mark.asyncio
    async def test_get_bot_status_missing(
        self, cache: RedisCache
    ) -> None:
        """get_bot_status when not cached should return None."""
        result = await cache.get_bot_status()
        assert result is None

    @pytest.mark.asyncio
    async def test_bot_status_key(self, cache: RedisCache) -> None:
        """Bot status should be stored under 'bot:status'."""
        await cache.cache_bot_status({"active": True})

        raw = await cache.get("bot:status")
        assert raw is not None
        parsed = json.loads(raw)
        assert parsed["active"] is True
