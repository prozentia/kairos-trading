"""Binance REST API adapter.

Handles all synchronous-style API calls: order placement, balance
queries, historical klines, and exchange info.  Built-in rate limiting
ensures we stay within Binance's request weight limits.

Dependencies: aiohttp (or httpx)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any, Callable, Awaitable
from urllib.parse import urlencode

from adapters.exchanges.base import BaseExchange

logger = logging.getLogger(__name__)

# Binance REST endpoints
BINANCE_REST_BASE = "https://api.binance.com"
BINANCE_TESTNET_BASE = "https://testnet.binance.vision"

# Rate limit: max requests per minute (Binance allows 1200 weight/min)
DEFAULT_RATE_LIMIT_DELAY = 0.1  # 100 ms between calls


class BinanceREST(BaseExchange):
    """Binance REST API adapter with rate limiting.

    All methods are async and use aiohttp under the hood.
    The adapter signs requests using HMAC-SHA256 when authentication
    is required (orders, balances, user-data listen keys).
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._rate_limit_delay = rate_limit_delay

        self._base_url = BINANCE_TESTNET_BASE if testnet else BINANCE_REST_BASE
        self._session: Any = None  # aiohttp.ClientSession
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the HTTP client session.

        Also validates connectivity by fetching /api/v3/ping.
        """
        raise NotImplementedError("BinanceREST.connect() not yet implemented")

    async def disconnect(self) -> None:
        """Close the HTTP client session."""
        raise NotImplementedError("BinanceREST.disconnect() not yet implemented")

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    async def _rate_limit(self) -> None:
        """Wait if needed to respect rate-limit delay between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.monotonic()

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add timestamp and HMAC-SHA256 signature to request params.

        Parameters
        ----------
        params : dict
            Query parameters to sign.

        Returns
        -------
        dict
            Params with 'timestamp' and 'signature' added.
        """
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any] | list[Any]:
        """Send an HTTP request to Binance.

        Parameters
        ----------
        method : str
            "GET", "POST", "DELETE".
        endpoint : str
            API path, e.g. "/api/v3/order".
        params : dict | None
            Query or body parameters.
        signed : bool
            Whether to sign the request (adds timestamp + signature).

        Returns
        -------
        dict | list
            Parsed JSON response.
        """
        raise NotImplementedError("BinanceREST._request() not yet implemented")

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    async def get_historical_klines(
        self,
        pair: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch historical klines from GET /api/v3/klines.

        Returns a list of dicts with:
        timestamp, open, high, low, close, volume.
        """
        raise NotImplementedError("BinanceREST.get_historical_klines() not yet implemented")

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    async def place_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> dict[str, Any]:
        """Place an order via POST /api/v3/order.

        Returns the order response including orderId and status.
        """
        raise NotImplementedError("BinanceREST.place_order() not yet implemented")

    async def cancel_order(self, pair: str, order_id: str) -> bool:
        """Cancel an order via DELETE /api/v3/order.

        Returns True if successfully cancelled.
        """
        raise NotImplementedError("BinanceREST.cancel_order() not yet implemented")

    async def set_stop_loss(
        self,
        pair: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Place a STOP_LOSS_LIMIT order.

        Uses a small offset from stop_price as the limit price
        to ensure execution.
        """
        raise NotImplementedError("BinanceREST.set_stop_loss() not yet implemented")

    # ------------------------------------------------------------------
    # Account queries
    # ------------------------------------------------------------------

    async def get_balance(self, asset: str) -> float:
        """Get free balance for a single asset from GET /api/v3/account."""
        raise NotImplementedError("BinanceREST.get_balance() not yet implemented")

    async def get_all_balances(self) -> dict[str, float]:
        """Get all non-zero free balances from GET /api/v3/account."""
        raise NotImplementedError("BinanceREST.get_all_balances() not yet implemented")

    # ------------------------------------------------------------------
    # Exchange metadata
    # ------------------------------------------------------------------

    async def get_exchange_info(self, pair: str) -> dict[str, Any]:
        """Fetch trading rules for a pair from GET /api/v3/exchangeInfo.

        Extracts and returns: min_qty, step_size, tick_size, min_notional.
        """
        raise NotImplementedError("BinanceREST.get_exchange_info() not yet implemented")

    # ------------------------------------------------------------------
    # User-data listen key management
    # ------------------------------------------------------------------

    async def create_listen_key(self) -> str:
        """Create a user-data stream listen key via POST /api/v3/userDataStream."""
        raise NotImplementedError("BinanceREST.create_listen_key() not yet implemented")

    async def keepalive_listen_key(self, listen_key: str) -> None:
        """Keepalive a listen key via PUT /api/v3/userDataStream."""
        raise NotImplementedError("BinanceREST.keepalive_listen_key() not yet implemented")

    # ------------------------------------------------------------------
    # Stream subscriptions (not applicable for REST -- raise)
    # ------------------------------------------------------------------

    async def subscribe_klines(
        self, pairs: list[str], timeframe: str,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Not applicable for REST adapter -- use BinanceWebSocket."""
        raise NotImplementedError("Use BinanceWebSocket for stream subscriptions")

    async def subscribe_ticker(
        self, pairs: list[str],
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Not applicable for REST adapter -- use BinanceWebSocket."""
        raise NotImplementedError("Use BinanceWebSocket for stream subscriptions")

    async def subscribe_user_data(
        self, callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Not applicable for REST adapter -- use BinanceWebSocket."""
        raise NotImplementedError("Use BinanceWebSocket for stream subscriptions")
