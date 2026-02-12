"""Binance REST API adapter for order management and account queries.

Handles all synchronous REST interactions with Binance: placing orders,
querying balances, fetching historical klines, and retrieving exchange info.
Built-in rate limiting ensures we stay within Binance's request weight limits.

Dependencies: aiohttp
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from urllib.parse import urlencode

import aiohttp

from adapters.exchanges.base import BaseExchange
from core.models import Candle

logger = logging.getLogger(__name__)

# Binance REST API base URLs
BINANCE_REST_BASE = "https://api.binance.com"
BINANCE_TESTNET_BASE = "https://testnet.binance.vision"

# Rate limit: max requests per minute (Binance allows 1200 weight/min)
DEFAULT_RATE_LIMIT_DELAY = 0.1  # 100 ms between calls

# Retry settings for transient failures
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds


class BinanceAPIError(Exception):
    """Custom exception for Binance API errors.

    Attributes
    ----------
    http_status : int
        HTTP response status code.
    error_code : int
        Binance-specific error code.
    error_message : str
        Human-readable error message from Binance.
    """

    def __init__(self, http_status: int, error_code: int, error_message: str) -> None:
        self.http_status = http_status
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(
            f"Binance API error [{http_status}] code={error_code}: {error_message}"
        )


class BinanceREST(BaseExchange):
    """Binance REST API adapter with rate limiting and retry logic.

    All methods are async and use aiohttp under the hood.
    The adapter signs requests using HMAC-SHA256 when authentication
    is required (orders, balances, user-data listen keys).

    Parameters
    ----------
    api_key : str
        Binance API key.
    api_secret : str
        Binance API secret.
    testnet : bool
        If True, use the Binance testnet endpoint.
    rate_limit_delay : float
        Minimum delay in seconds between consecutive requests.
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
        self._session: aiohttp.ClientSession | None = None
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the HTTP client session and validate connectivity."""
        if self._session is None or self._session.closed:
            headers = {}
            if self._api_key:
                headers["X-MBX-APIKEY"] = self._api_key
            self._session = aiohttp.ClientSession(headers=headers)
            logger.info("BinanceREST connected (testnet=%s)", self._testnet)

    async def disconnect(self) -> None:
        """Close the HTTP client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.info("BinanceREST disconnected")

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
        """Send an HTTP request to Binance with retry and rate-limit logic.

        Parameters
        ----------
        method : str
            "GET", "POST", "DELETE", "PUT".
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

        Raises
        ------
        BinanceAPIError
            When the API returns an error after all retries.
        ConnectionError
            When unable to connect after all retries.
        """
        if self._session is None or self._session.closed:
            await self.connect()

        if params is None:
            params = {}

        url = f"{self._base_url}{endpoint}"

        for attempt in range(1, MAX_RETRIES + 1):
            # Respect rate limiting
            await self._rate_limit()

            # Sign on each attempt (timestamp must be fresh)
            req_params = dict(params)
            if signed:
                req_params = self._sign(req_params)

            try:
                async with self._session.request(
                    method, url, params=req_params
                ) as resp:
                    data = await resp.json()

                    # Handle rate limiting (HTTP 429)
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 1))
                        logger.warning(
                            "Rate limited by Binance, retrying in %ds "
                            "(attempt %d/%d)",
                            retry_after, attempt, MAX_RETRIES,
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    # Handle server errors (5xx) with retry
                    if resp.status >= 500:
                        if attempt < MAX_RETRIES:
                            wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                            logger.warning(
                                "Binance server error %d, retrying in %.1fs "
                                "(attempt %d/%d)",
                                resp.status, wait, attempt, MAX_RETRIES,
                            )
                            await asyncio.sleep(wait)
                            continue
                        raise BinanceAPIError(
                            resp.status,
                            data.get("code", -1),
                            data.get("msg", "Server error"),
                        )

                    # Handle client errors (4xx)
                    if resp.status >= 400:
                        raise BinanceAPIError(
                            resp.status,
                            data.get("code", -1),
                            data.get("msg", "Unknown error"),
                        )

                    return data

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt == MAX_RETRIES:
                    logger.error(
                        "Request failed after %d attempts: %s %s — %s",
                        MAX_RETRIES, method, endpoint, exc,
                    )
                    raise ConnectionError(
                        f"Failed to connect to Binance after "
                        f"{MAX_RETRIES} attempts: {exc}"
                    ) from exc
                wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "Request error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt, MAX_RETRIES, wait, exc,
                )
                await asyncio.sleep(wait)

        raise ConnectionError("Request failed unexpectedly")

    # ------------------------------------------------------------------
    # Account queries
    # ------------------------------------------------------------------

    async def get_account_info(self) -> dict[str, Any]:
        """Fetch full account information (balances, permissions).

        Returns
        -------
        dict
            Binance account info including balances and permissions.
        """
        data = await self._request("GET", "/api/v3/account", signed=True)
        return data

    async def get_balance(self, asset: str) -> float:
        """Get free balance for a single asset from GET /api/v3/account.

        Parameters
        ----------
        asset : str
            Asset symbol, e.g. "USDT", "BTC".

        Returns
        -------
        float
            Available (free) balance.
        """
        account = await self.get_account_info()
        for balance in account.get("balances", []):
            if balance["asset"] == asset:
                return float(balance["free"])
        return 0.0

    async def get_all_balances(self) -> dict[str, float]:
        """Get all non-zero free balances from GET /api/v3/account.

        Returns
        -------
        dict[str, float]
            Mapping of asset symbol to free balance.
        """
        account = await self.get_account_info()
        result: dict[str, float] = {}
        for balance in account.get("balances", []):
            free = float(balance["free"])
            locked = float(balance.get("locked", 0))
            if free > 0 or locked > 0:
                result[balance["asset"]] = free
        return result

    # ------------------------------------------------------------------
    # Market data (REST)
    # ------------------------------------------------------------------

    async def get_ticker_price(self, symbol: str) -> float:
        """Get current ticker price for a symbol.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".

        Returns
        -------
        float
            Current price.
        """
        data = await self._request(
            "GET", "/api/v3/ticker/price", params={"symbol": symbol}
        )
        return float(data["price"])

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        """Get order book depth for a symbol.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        limit : int
            Number of bid/ask levels (5, 10, 20, 50, 100, 500, 1000, 5000).

        Returns
        -------
        dict
            Order book with 'bids' and 'asks' arrays.
        """
        data = await self._request(
            "GET", "/api/v3/depth",
            params={"symbol": symbol, "limit": limit},
        )
        return data

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
    ) -> list[Candle]:
        """Fetch historical klines and convert to core Candle models.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        interval : str
            Kline interval, e.g. "1m", "5m", "1h".
        limit : int
            Number of klines to fetch (max 1000).

        Returns
        -------
        list[Candle]
            List of Candle objects from the core domain.
        """
        raw = await self._request(
            "GET", "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        candles: list[Candle] = []
        for k in raw:
            # Binance kline: [open_time, O, H, L, C, volume, close_time, ...]
            candle = Candle(
                timestamp=datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                pair=symbol,
                timeframe=interval,
                is_closed=True,
            )
            candles.append(candle)
        return candles

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
        candles = await self.get_klines(pair, timeframe, limit)
        return [c.to_dict() for c in candles]

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> dict[str, Any]:
        """Place a market order.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        side : str
            "BUY" or "SELL".
        quantity : float
            Order quantity in base asset.

        Returns
        -------
        dict
            Binance order response.
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": f"{quantity}",
        }
        data = await self._request(
            "POST", "/api/v3/order", params=params, signed=True
        )
        logger.info(
            "Market order placed: %s %s qty=%s — orderId=%s",
            side, symbol, quantity, data.get("orderId"),
        )
        return data

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
    ) -> dict[str, Any]:
        """Place a limit order.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".
        side : str
            "BUY" or "SELL".
        quantity : float
            Order quantity in base asset.
        price : float
            Limit price.

        Returns
        -------
        dict
            Binance order response.
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": f"{quantity}",
            "price": f"{price}",
        }
        data = await self._request(
            "POST", "/api/v3/order", params=params, signed=True
        )
        logger.info(
            "Limit order placed: %s %s qty=%s price=%s — orderId=%s",
            side, symbol, quantity, price, data.get("orderId"),
        )
        return data

    async def place_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> dict[str, Any]:
        """Place an order via POST /api/v3/order (BaseExchange interface).

        Parameters
        ----------
        pair : str
            Trading pair, e.g. "BTCUSDT".
        side : str
            "BUY" or "SELL".
        quantity : float
            Order quantity in base asset.
        order_type : str
            "MARKET" or "LIMIT".
        price : float | None
            Required for LIMIT orders.

        Returns
        -------
        dict
            Exchange order response including orderId and status.
        """
        if order_type == "LIMIT" and price is not None:
            return await self.place_limit_order(pair, side, quantity, price)
        return await self.place_market_order(pair, side, quantity)

    async def cancel_order(self, pair: str, order_id: str) -> bool:
        """Cancel an order via DELETE /api/v3/order.

        Parameters
        ----------
        pair : str
            Trading pair, e.g. "BTCUSDT".
        order_id : str
            The Binance order ID.

        Returns
        -------
        bool
            True if successfully cancelled.
        """
        params = {"symbol": pair, "orderId": int(order_id)}
        try:
            await self._request(
                "DELETE", "/api/v3/order", params=params, signed=True
            )
            logger.info("Order cancelled: %s orderId=%s", pair, order_id)
            return True
        except BinanceAPIError as exc:
            logger.error("Failed to cancel order %s: %s", order_id, exc)
            return False

    async def set_stop_loss(
        self,
        pair: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Place a STOP_LOSS_LIMIT order.

        Uses a small offset from stop_price (0.1% below) as the limit
        price to ensure execution during fast price moves.

        Parameters
        ----------
        pair : str
            Trading pair.
        quantity : float
            Quantity to sell.
        stop_price : float
            Trigger price for the stop.

        Returns
        -------
        dict
            Binance order response.
        """
        limit_price = stop_price * 0.999
        params = {
            "symbol": pair,
            "side": "SELL",
            "type": "STOP_LOSS_LIMIT",
            "timeInForce": "GTC",
            "quantity": f"{quantity}",
            "stopPrice": f"{stop_price}",
            "price": f"{limit_price}",
        }
        data = await self._request(
            "POST", "/api/v3/order", params=params, signed=True
        )
        logger.info(
            "Stop-loss placed: %s qty=%s stop=%s — orderId=%s",
            pair, quantity, stop_price, data.get("orderId"),
        )
        return data

    async def get_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Get all open orders for a symbol.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTCUSDT".

        Returns
        -------
        list[dict]
            List of open order records.
        """
        params = {"symbol": symbol}
        data = await self._request(
            "GET", "/api/v3/openOrders", params=params, signed=True
        )
        return data

    async def get_order_status(
        self, symbol: str, order_id: str
    ) -> dict[str, Any]:
        """Get the status of a specific order.

        Parameters
        ----------
        symbol : str
            Trading pair.
        order_id : str
            The Binance order ID.

        Returns
        -------
        dict
            Order status record.
        """
        params = {"symbol": symbol, "orderId": int(order_id)}
        data = await self._request(
            "GET", "/api/v3/order", params=params, signed=True
        )
        return data

    # ------------------------------------------------------------------
    # Exchange metadata
    # ------------------------------------------------------------------

    async def get_exchange_info(self, pair: str) -> dict[str, Any]:
        """Fetch trading rules for a pair from GET /api/v3/exchangeInfo.

        Extracts and returns: min_qty, step_size, tick_size, min_notional.

        Parameters
        ----------
        pair : str
            Trading pair, e.g. "BTCUSDT".

        Returns
        -------
        dict
            Contains at minimum: min_qty, step_size, tick_size, min_notional.
        """
        data = await self._request(
            "GET", "/api/v3/exchangeInfo", params={"symbol": pair}
        )
        result: dict[str, Any] = {
            "symbol": pair,
            "min_qty": 0.0,
            "step_size": 0.0,
            "tick_size": 0.0,
            "min_notional": 0.0,
        }

        for symbol_info in data.get("symbols", []):
            if symbol_info["symbol"] == pair:
                result["raw"] = symbol_info
                for f in symbol_info.get("filters", []):
                    if f["filterType"] == "LOT_SIZE":
                        result["min_qty"] = float(f["minQty"])
                        result["step_size"] = float(f["stepSize"])
                    elif f["filterType"] == "PRICE_FILTER":
                        result["tick_size"] = float(f["tickSize"])
                    elif f["filterType"] in ("NOTIONAL", "MIN_NOTIONAL"):
                        result["min_notional"] = float(
                            f.get("minNotional", 0)
                        )
                break

        return result

    # ------------------------------------------------------------------
    # User-data listen key management
    # ------------------------------------------------------------------

    async def create_listen_key(self) -> str:
        """Create a user-data stream listen key via POST /api/v3/userDataStream.

        Returns
        -------
        str
            The listen key string.
        """
        data = await self._request("POST", "/api/v3/userDataStream")
        return data["listenKey"]

    async def keepalive_listen_key(self, listen_key: str) -> None:
        """Keepalive a listen key via PUT /api/v3/userDataStream.

        Parameters
        ----------
        listen_key : str
            The listen key to keep alive.
        """
        await self._request(
            "PUT", "/api/v3/userDataStream",
            params={"listenKey": listen_key},
        )

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
