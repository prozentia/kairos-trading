"""Unit tests for the BinanceREST adapter.

All HTTP calls are mocked using aiohttp test utilities. No real network
requests are made during testing.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from adapters.exchanges.binance_rest import BinanceAPIError, BinanceREST
from core.models import Candle


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def api_key() -> str:
    return "test_api_key_123"


@pytest.fixture
def api_secret() -> str:
    return "test_api_secret_456"


@pytest_asyncio.fixture
async def client(api_key: str, api_secret: str) -> BinanceREST:
    """Create a BinanceREST client without connecting."""
    return BinanceREST(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True,
        rate_limit_delay=0.0,  # No delay in tests
    )


# ======================================================================
# Helper to mock _request
# ======================================================================

def mock_request(client: BinanceREST, return_value: Any) -> AsyncMock:
    """Patch the _request method on the client."""
    mock = AsyncMock(return_value=return_value)
    client._request = mock
    return mock


# ======================================================================
# Tests: Constructor & Config
# ======================================================================

class TestBinanceRESTConfig:
    """Test configuration and initialization."""

    def test_default_base_url(self) -> None:
        """Default URL should be production Binance."""
        client = BinanceREST()
        assert client._base_url == "https://api.binance.com"

    def test_testnet_base_url(self) -> None:
        """Testnet flag should switch to testnet URL."""
        client = BinanceREST(testnet=True)
        assert client._base_url == "https://testnet.binance.vision"

    def test_api_key_stored(self, api_key: str, api_secret: str) -> None:
        """API credentials should be stored."""
        client = BinanceREST(api_key=api_key, api_secret=api_secret)
        assert client._api_key == api_key
        assert client._api_secret == api_secret


# ======================================================================
# Tests: Signing
# ======================================================================

class TestSigning:
    """Test HMAC-SHA256 request signing."""

    def test_sign_adds_timestamp_and_signature(
        self, client: BinanceREST
    ) -> None:
        """Signing should add timestamp and valid HMAC signature."""
        params = {"symbol": "BTCUSDT", "side": "BUY"}
        signed = client._sign(params)

        assert "timestamp" in signed
        assert "signature" in signed
        assert isinstance(signed["timestamp"], int)

    def test_sign_produces_valid_hmac(
        self, client: BinanceREST, api_secret: str
    ) -> None:
        """Signature should match manual HMAC-SHA256 computation."""
        params = {"symbol": "BTCUSDT"}
        signed = client._sign(params)

        # Reconstruct what the signature should be
        from urllib.parse import urlencode

        # Remove signature to reconstruct query string
        sig = signed.pop("signature")
        query_string = urlencode(signed)
        expected_sig = hmac.new(
            api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        assert sig == expected_sig


# ======================================================================
# Tests: Account Queries
# ======================================================================

class TestAccountQueries:
    """Test account information and balance queries."""

    @pytest.mark.asyncio
    async def test_get_account_info(self, client: BinanceREST) -> None:
        """get_account_info should return the raw account data."""
        account_data = {
            "balances": [
                {"asset": "BTC", "free": "0.001", "locked": "0.0"},
                {"asset": "USDT", "free": "150.50", "locked": "0.0"},
            ],
            "permissions": ["SPOT"],
        }
        mock_request(client, account_data)

        result = await client.get_account_info()

        assert result == account_data

    @pytest.mark.asyncio
    async def test_get_balance_existing_asset(
        self, client: BinanceREST
    ) -> None:
        """get_balance should return the free balance for an existing asset."""
        account_data = {
            "balances": [
                {"asset": "USDT", "free": "150.50", "locked": "0.0"},
                {"asset": "BTC", "free": "0.001", "locked": "0.0"},
            ]
        }
        mock_request(client, account_data)

        balance = await client.get_balance("USDT")

        assert balance == 150.50

    @pytest.mark.asyncio
    async def test_get_balance_missing_asset(
        self, client: BinanceREST
    ) -> None:
        """get_balance should return 0.0 for a non-existent asset."""
        account_data = {
            "balances": [
                {"asset": "USDT", "free": "100.0", "locked": "0.0"},
            ]
        }
        mock_request(client, account_data)

        balance = await client.get_balance("ETH")

        assert balance == 0.0

    @pytest.mark.asyncio
    async def test_get_all_balances(self, client: BinanceREST) -> None:
        """get_all_balances should return only non-zero balances."""
        account_data = {
            "balances": [
                {"asset": "USDT", "free": "100.0", "locked": "0.0"},
                {"asset": "BTC", "free": "0.0", "locked": "0.0"},
                {"asset": "ETH", "free": "0.5", "locked": "0.1"},
            ]
        }
        mock_request(client, account_data)

        balances = await client.get_all_balances()

        assert "USDT" in balances
        assert "ETH" in balances
        assert "BTC" not in balances
        assert balances["USDT"] == 100.0
        assert balances["ETH"] == 0.5


# ======================================================================
# Tests: Market Data
# ======================================================================

class TestMarketData:
    """Test market data retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_ticker_price(self, client: BinanceREST) -> None:
        """get_ticker_price should return the parsed price."""
        mock_request(client, {"symbol": "BTCUSDT", "price": "45000.50"})

        price = await client.get_ticker_price("BTCUSDT")

        assert price == 45000.50

    @pytest.mark.asyncio
    async def test_get_orderbook(self, client: BinanceREST) -> None:
        """get_orderbook should return bids and asks."""
        book = {
            "bids": [["45000.0", "1.0"], ["44999.0", "0.5"]],
            "asks": [["45001.0", "0.8"], ["45002.0", "1.2"]],
        }
        mock_request(client, book)

        result = await client.get_orderbook("BTCUSDT", limit=10)

        assert "bids" in result
        assert "asks" in result
        assert len(result["bids"]) == 2

    @pytest.mark.asyncio
    async def test_get_klines_returns_candles(
        self, client: BinanceREST
    ) -> None:
        """get_klines should convert raw Binance data to Candle objects."""
        raw_klines = [
            [
                1704067200000,  # open time (2024-01-01 00:00:00 UTC)
                "42000.00",  # open
                "42500.00",  # high
                "41800.00",  # low
                "42300.00",  # close
                "100.5",  # volume
                1704070799999,  # close time
                "4231500.0",  # quote volume
                50,  # trades
                "60.3",  # taker buy base
                "2543100.0",  # taker buy quote
                "0",  # ignore
            ],
            [
                1704070800000,
                "42300.00",
                "42800.00",
                "42100.00",
                "42600.00",
                "85.2",
                1704074399999,
                "3629520.0",
                35,
                "40.1",
                "1708260.0",
                "0",
            ],
        ]
        mock_request(client, raw_klines)

        candles = await client.get_klines("BTCUSDT", "1h", limit=2)

        assert len(candles) == 2
        assert isinstance(candles[0], Candle)
        assert candles[0].pair == "BTCUSDT"
        assert candles[0].timeframe == "1h"
        assert candles[0].open == 42000.00
        assert candles[0].high == 42500.00
        assert candles[0].low == 41800.00
        assert candles[0].close == 42300.00
        assert candles[0].volume == 100.5
        assert candles[0].is_closed is True

    @pytest.mark.asyncio
    async def test_get_historical_klines_returns_dicts(
        self, client: BinanceREST
    ) -> None:
        """get_historical_klines should return list of dicts."""
        raw_klines = [
            [
                1704067200000,
                "42000.00",
                "42500.00",
                "41800.00",
                "42300.00",
                "100.5",
                1704070799999,
                "4231500.0",
                50,
                "60.3",
                "2543100.0",
                "0",
            ],
        ]
        mock_request(client, raw_klines)

        result = await client.get_historical_klines("BTCUSDT", "5m", 1)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["pair"] == "BTCUSDT"
        assert result[0]["open"] == 42000.00


# ======================================================================
# Tests: Order Management
# ======================================================================

class TestOrderManagement:
    """Test order placement, cancellation, and queries."""

    @pytest.mark.asyncio
    async def test_place_market_order(self, client: BinanceREST) -> None:
        """place_market_order should send correct params."""
        order_response = {
            "orderId": 12345,
            "symbol": "BTCUSDT",
            "status": "FILLED",
            "type": "MARKET",
            "side": "BUY",
        }
        mock = mock_request(client, order_response)

        result = await client.place_market_order("BTCUSDT", "BUY", 0.001)

        assert result["orderId"] == 12345
        assert result["status"] == "FILLED"
        mock.assert_called_once()
        call_args = mock.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/api/v3/order"

    @pytest.mark.asyncio
    async def test_place_limit_order(self, client: BinanceREST) -> None:
        """place_limit_order should include price and timeInForce."""
        order_response = {
            "orderId": 12346,
            "symbol": "BTCUSDT",
            "status": "NEW",
            "type": "LIMIT",
        }
        mock = mock_request(client, order_response)

        result = await client.place_limit_order(
            "BTCUSDT", "SELL", 0.001, 50000.0
        )

        assert result["orderId"] == 12346
        call_kwargs = mock.call_args[1]
        params = call_kwargs["params"]
        assert params["type"] == "LIMIT"
        assert params["timeInForce"] == "GTC"
        assert params["price"] == "50000.0"

    @pytest.mark.asyncio
    async def test_place_order_market(self, client: BinanceREST) -> None:
        """place_order with MARKET type should delegate to place_market_order."""
        order_response = {"orderId": 100, "status": "FILLED"}
        mock_request(client, order_response)

        result = await client.place_order(
            "BTCUSDT", "BUY", 0.001, order_type="MARKET"
        )

        assert result["orderId"] == 100

    @pytest.mark.asyncio
    async def test_place_order_limit(self, client: BinanceREST) -> None:
        """place_order with LIMIT type should delegate to place_limit_order."""
        order_response = {"orderId": 101, "status": "NEW"}
        mock_request(client, order_response)

        result = await client.place_order(
            "BTCUSDT", "SELL", 0.001, order_type="LIMIT", price=50000.0
        )

        assert result["orderId"] == 101

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, client: BinanceREST) -> None:
        """cancel_order should return True on success."""
        mock_request(client, {"orderId": 12345, "status": "CANCELED"})

        result = await client.cancel_order("BTCUSDT", "12345")

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, client: BinanceREST) -> None:
        """cancel_order should return False when API returns an error."""
        client._request = AsyncMock(
            side_effect=BinanceAPIError(400, -2011, "Unknown order")
        )

        result = await client.cancel_order("BTCUSDT", "99999")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_stop_loss(self, client: BinanceREST) -> None:
        """set_stop_loss should place a STOP_LOSS_LIMIT order."""
        order_response = {
            "orderId": 200,
            "type": "STOP_LOSS_LIMIT",
            "status": "NEW",
        }
        mock = mock_request(client, order_response)

        result = await client.set_stop_loss("BTCUSDT", 0.001, 40000.0)

        assert result["orderId"] == 200
        call_kwargs = mock.call_args[1]
        params = call_kwargs["params"]
        assert params["type"] == "STOP_LOSS_LIMIT"
        assert params["stopPrice"] == "40000.0"
        # Limit price should be slightly below stop price
        assert float(params["price"]) < 40000.0

    @pytest.mark.asyncio
    async def test_get_open_orders(self, client: BinanceREST) -> None:
        """get_open_orders should return list of order dicts."""
        orders = [
            {"orderId": 1, "status": "NEW"},
            {"orderId": 2, "status": "PARTIALLY_FILLED"},
        ]
        mock_request(client, orders)

        result = await client.get_open_orders("BTCUSDT")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_order_status(self, client: BinanceREST) -> None:
        """get_order_status should return the order details."""
        order = {"orderId": 12345, "status": "FILLED", "symbol": "BTCUSDT"}
        mock_request(client, order)

        result = await client.get_order_status("BTCUSDT", "12345")

        assert result["status"] == "FILLED"


# ======================================================================
# Tests: Exchange Info
# ======================================================================

class TestExchangeInfo:
    """Test exchange metadata retrieval."""

    @pytest.mark.asyncio
    async def test_get_exchange_info(self, client: BinanceREST) -> None:
        """get_exchange_info should extract filters from symbol info."""
        exchange_data = {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "status": "TRADING",
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001000",
                            "stepSize": "0.00001000",
                        },
                        {
                            "filterType": "PRICE_FILTER",
                            "tickSize": "0.01000000",
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "10.00000000",
                        },
                    ],
                }
            ]
        }
        mock_request(client, exchange_data)

        result = await client.get_exchange_info("BTCUSDT")

        assert result["symbol"] == "BTCUSDT"
        assert result["min_qty"] == 0.00001
        assert result["step_size"] == 0.00001
        assert result["tick_size"] == 0.01
        assert result["min_notional"] == 10.0
        assert "raw" in result

    @pytest.mark.asyncio
    async def test_get_exchange_info_unknown_pair(
        self, client: BinanceREST
    ) -> None:
        """get_exchange_info for unknown pair should return defaults."""
        mock_request(client, {"symbols": []})

        result = await client.get_exchange_info("XYZUSDT")

        assert result["symbol"] == "XYZUSDT"
        assert result["min_qty"] == 0.0
        assert result["step_size"] == 0.0


# ======================================================================
# Tests: Listen Key
# ======================================================================

class TestListenKey:
    """Test user-data stream listen key management."""

    @pytest.mark.asyncio
    async def test_create_listen_key(self, client: BinanceREST) -> None:
        """create_listen_key should return the listen key string."""
        mock_request(client, {"listenKey": "abc123def456"})

        key = await client.create_listen_key()

        assert key == "abc123def456"

    @pytest.mark.asyncio
    async def test_keepalive_listen_key(self, client: BinanceREST) -> None:
        """keepalive_listen_key should not raise."""
        mock = mock_request(client, {})

        await client.keepalive_listen_key("abc123def456")

        mock.assert_called_once()


# ======================================================================
# Tests: WebSocket stubs raise NotImplementedError
# ======================================================================

class TestWebSocketStubs:
    """WS methods should raise NotImplementedError."""

    @pytest.mark.asyncio
    async def test_subscribe_klines_raises(
        self, client: BinanceREST
    ) -> None:
        with pytest.raises(NotImplementedError):
            await client.subscribe_klines(["BTCUSDT"], "1m", AsyncMock())

    @pytest.mark.asyncio
    async def test_subscribe_ticker_raises(
        self, client: BinanceREST
    ) -> None:
        with pytest.raises(NotImplementedError):
            await client.subscribe_ticker(["BTCUSDT"], AsyncMock())

    @pytest.mark.asyncio
    async def test_subscribe_user_data_raises(
        self, client: BinanceREST
    ) -> None:
        with pytest.raises(NotImplementedError):
            await client.subscribe_user_data(AsyncMock())


# ======================================================================
# Tests: BinanceAPIError
# ======================================================================

class TestBinanceAPIError:
    """Test the custom error class."""

    def test_error_attributes(self) -> None:
        """Error should store all attributes."""
        err = BinanceAPIError(400, -1021, "Timestamp outside recv window")
        assert err.http_status == 400
        assert err.error_code == -1021
        assert err.error_message == "Timestamp outside recv window"

    def test_error_string(self) -> None:
        """Error string should be human-readable."""
        err = BinanceAPIError(400, -1021, "Bad timestamp")
        assert "400" in str(err)
        assert "-1021" in str(err)
        assert "Bad timestamp" in str(err)
