"""Market service - price data, candles, ticker, order book.

Fetches market data from Redis cache when available, otherwise falls back
to direct exchange REST calls via httpx.  The Binance public API endpoints
do not require authentication for market data.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

# Binance public REST base URL
BINANCE_API_BASE = "https://api.binance.com"


class MarketService:
    """Fetches market data from the exchange adapter or cache (Redis).

    In production, price data flows through the Binance WebSocket adapter
    and is cached in Redis.  This service reads from Redis first, falling
    back to the REST adapter for historical data.
    """

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Spot price
    # ------------------------------------------------------------------

    async def get_price(self, pair: str) -> dict[str, Any]:
        """Get current price for a pair.

        Returns {"pair": "BTCUSDT", "price": 98250.5, "timestamp": "..."}.
        """
        symbol = pair.upper().replace("/", "")

        # Try Redis cache first
        if self._redis:
            cached = await self._redis.get(f"price:{symbol}")
            if cached:
                return {
                    "pair": symbol,
                    "price": float(cached),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "cache",
                }

        # Fallback to Binance REST
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BINANCE_API_BASE}/api/v3/ticker/price",
                    params={"symbol": symbol},
                )
                resp.raise_for_status()
                data = resp.json()
                price = float(data["price"])

                # Cache for 5 seconds
                if self._redis:
                    await self._redis.setex(f"price:{symbol}", 5, str(price))

                return {
                    "pair": symbol,
                    "price": price,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "binance",
                }
        except Exception as exc:
            return {
                "pair": symbol,
                "price": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }

    async def get_all_prices(self) -> list[dict[str, Any]]:
        """Get prices for all active USDT pairs.

        Returns list of {"pair", "price", "change_24h_pct"}.
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{BINANCE_API_BASE}/api/v3/ticker/24hr")
                resp.raise_for_status()
                tickers = resp.json()

                # Filter to USDT pairs only
                results = []
                for t in tickers:
                    if t["symbol"].endswith("USDT"):
                        results.append({
                            "pair": t["symbol"],
                            "price": float(t["lastPrice"]),
                            "change_24h_pct": float(t["priceChangePercent"]),
                            "volume_24h": float(t["quoteVolume"]),
                        })

                # Sort by volume descending
                results.sort(key=lambda x: x["volume_24h"], reverse=True)
                return results[:50]  # Top 50 by volume
        except Exception:
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
        symbol = pair.upper().replace("/", "")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{BINANCE_API_BASE}/api/v3/klines",
                    params={
                        "symbol": symbol,
                        "interval": timeframe,
                        "limit": min(limit, 1000),
                    },
                )
                resp.raise_for_status()
                raw_klines = resp.json()

                candles = []
                for k in raw_klines:
                    candles.append({
                        "timestamp": datetime.fromtimestamp(
                            k[0] / 1000, tz=timezone.utc
                        ).isoformat(),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    })
                return candles
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Ticker
    # ------------------------------------------------------------------

    async def get_ticker(self, pair: str) -> dict[str, Any]:
        """Get 24h ticker statistics."""
        symbol = pair.upper().replace("/", "")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BINANCE_API_BASE}/api/v3/ticker/24hr",
                    params={"symbol": symbol},
                )
                resp.raise_for_status()
                data = resp.json()

                return {
                    "pair": symbol,
                    "price": float(data["lastPrice"]),
                    "high_24h": float(data["highPrice"]),
                    "low_24h": float(data["lowPrice"]),
                    "volume_24h": float(data["quoteVolume"]),
                    "change_24h_pct": float(data["priceChangePercent"]),
                }
        except Exception:
            return {
                "pair": symbol,
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
        symbol = pair.upper().replace("/", "")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BINANCE_API_BASE}/api/v3/depth",
                    params={"symbol": symbol, "limit": min(depth, 100)},
                )
                resp.raise_for_status()
                data = resp.json()

                return {
                    "pair": symbol,
                    "bids": [[float(b[0]), float(b[1])] for b in data.get("bids", [])],
                    "asks": [[float(a[0]), float(a[1])] for a in data.get("asks", [])],
                }
        except Exception:
            return {"pair": symbol, "bids": [], "asks": []}
