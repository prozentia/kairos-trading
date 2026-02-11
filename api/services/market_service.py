"""Market service - price data, candles, ticker, order book."""

from __future__ import annotations

from typing import Any


class MarketService:
    """Fetches market data from the exchange adapter or cache (Redis).

    In production, price data flows through the Binance WebSocket adapter
    and is cached in Redis.  This service reads from Redis first, falling
    back to the REST adapter for historical data.
    """

    def __init__(self, redis_client: Any = None, exchange_adapter: Any = None) -> None:
        self._redis = redis_client
        self._exchange = exchange_adapter

    # ------------------------------------------------------------------
    # Spot price
    # ------------------------------------------------------------------

    async def get_price(self, pair: str) -> dict[str, Any]:
        """Get current price for a pair.

        Returns {"pair": "BTCUSDT", "price": 98250.5, "timestamp": "..."}.
        """
        # TODO: read from Redis cache, fallback to REST
        return {"pair": pair.upper(), "price": 0.0, "timestamp": None}

    async def get_all_prices(self) -> list[dict[str, Any]]:
        """Get prices for all active pairs.

        Returns list of {"pair", "price", "change_24h_pct"}.
        """
        # TODO: read from Redis (all cached tickers)
        return []

    # ------------------------------------------------------------------
    # Candles
    # ------------------------------------------------------------------

    async def get_candles(
        self,
        pair: str,
        timeframe: str = "5m",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV candles.

        Returns list of {"timestamp", "open", "high", "low", "close", "volume"}.
        """
        # TODO: call exchange adapter REST endpoint
        return []

    # ------------------------------------------------------------------
    # Ticker
    # ------------------------------------------------------------------

    async def get_ticker(self, pair: str) -> dict[str, Any]:
        """Get 24h ticker statistics."""
        # TODO: call exchange adapter or cache
        return {
            "pair": pair.upper(),
            "price": 0.0,
            "high_24h": 0.0,
            "low_24h": 0.0,
            "volume_24h": 0.0,
            "change_24h_pct": 0.0,
        }

    # ------------------------------------------------------------------
    # Order book
    # ------------------------------------------------------------------

    async def get_orderbook(self, pair: str, depth: int = 20) -> dict[str, Any]:
        """Get order book snapshot.

        Returns {"pair", "bids": [[price, qty], ...], "asks": [[price, qty], ...]}.
        """
        # TODO: call exchange adapter
        return {"pair": pair.upper(), "bids": [], "asks": []}
