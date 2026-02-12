"""Unit tests for the BinanceWebSocket adapter.

All WebSocket connections are mocked. No real network connections are made.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from adapters.exchanges.binance_ws import (
    BINANCE_WS_BASE,
    BINANCE_WS_COMBINED,
    BINANCE_TESTNET_WS,
    BINANCE_TESTNET_COMBINED,
    BinanceWebSocket,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def ws_client() -> BinanceWebSocket:
    """Create a BinanceWebSocket client without connecting."""
    return BinanceWebSocket(
        api_key="test_key",
        api_secret="test_secret",
        testnet=False,
        reconnect_delay=0.01,
        max_reconnect_attempts=2,
    )


@pytest.fixture
def ws_client_testnet() -> BinanceWebSocket:
    """Create a testnet BinanceWebSocket client."""
    return BinanceWebSocket(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True,
    )


# ======================================================================
# Tests: Configuration
# ======================================================================

class TestBinanceWSConfig:
    """Test configuration and initialization."""

    def test_default_production_urls(self, ws_client: BinanceWebSocket) -> None:
        """Production URLs should be used by default."""
        assert ws_client._ws_base == BINANCE_WS_BASE
        assert ws_client._ws_combined == BINANCE_WS_COMBINED

    def test_testnet_urls(self, ws_client_testnet: BinanceWebSocket) -> None:
        """Testnet flag should switch to testnet URLs."""
        assert ws_client_testnet._ws_base == BINANCE_TESTNET_WS
        assert ws_client_testnet._ws_combined == BINANCE_TESTNET_COMBINED

    def test_credentials_stored(self, ws_client: BinanceWebSocket) -> None:
        """API credentials should be stored."""
        assert ws_client._api_key == "test_key"
        assert ws_client._api_secret == "test_secret"

    def test_initial_state(self, ws_client: BinanceWebSocket) -> None:
        """Initial state should be disconnected."""
        assert ws_client._running is False
        assert ws_client._market_ws is None
        assert ws_client._user_ws is None
        assert ws_client._listen_key is None
        assert len(ws_client._tasks) == 0
        assert len(ws_client._active_streams) == 0

    def test_reconnect_settings(self) -> None:
        """Custom reconnect settings should be stored."""
        client = BinanceWebSocket(
            reconnect_delay=10.0,
            max_reconnect_attempts=5,
        )
        assert client._reconnect_delay == 10.0
        assert client._max_reconnect_attempts == 5


# ======================================================================
# Tests: Connect / Disconnect
# ======================================================================

class TestConnectionLifecycle:
    """Test connection and disconnection."""

    @pytest.mark.asyncio
    async def test_connect_sets_running(self, ws_client: BinanceWebSocket) -> None:
        """connect() should set _running to True and create HTTP session."""
        await ws_client.connect()
        try:
            assert ws_client._running is True
            assert ws_client._http_session is not None
        finally:
            await ws_client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_clears_state(self, ws_client: BinanceWebSocket) -> None:
        """disconnect() should clear all state."""
        await ws_client.connect()
        ws_client._active_streams = ["btcusdt@kline_1m"]
        ws_client._listen_key = "some_key"

        await ws_client.disconnect()

        assert ws_client._running is False
        assert ws_client._market_ws is None
        assert ws_client._user_ws is None
        assert ws_client._listen_key is None
        assert len(ws_client._active_streams) == 0

    @pytest.mark.asyncio
    async def test_disconnect_cancels_tasks(self, ws_client: BinanceWebSocket) -> None:
        """disconnect() should cancel all background tasks."""
        await ws_client.connect()

        # Create a real asyncio task that sleeps
        async def long_running():
            await asyncio.sleep(3600)

        task = asyncio.create_task(long_running())
        ws_client._tasks.append(task)

        await ws_client.disconnect()

        assert task.cancelled() or task.done()
        assert len(ws_client._tasks) == 0


# ======================================================================
# Tests: Kline subscription
# ======================================================================

class TestKlineSubscription:
    """Test kline stream subscription."""

    @pytest.mark.asyncio
    async def test_subscribe_klines_registers_callbacks(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """subscribe_klines should register callbacks and add streams."""
        await ws_client.connect()

        callback = AsyncMock()
        with patch("adapters.exchanges.binance_ws.websockets") as mock_ws:
            mock_conn = AsyncMock()
            mock_ws.connect = AsyncMock(return_value=mock_conn)

            await ws_client.subscribe_klines(
                ["BTCUSDT", "ETHUSDT"], "1m", callback
            )

            assert "btcusdt@kline_1m" in ws_client._kline_callbacks
            assert "ethusdt@kline_1m" in ws_client._kline_callbacks
            assert "btcusdt@kline_1m" in ws_client._active_streams
            assert "ethusdt@kline_1m" in ws_client._active_streams

        await ws_client.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_klines_builds_correct_url(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """subscribe_klines should build the correct combined stream URL."""
        await ws_client.connect()

        callback = AsyncMock()
        with patch("adapters.exchanges.binance_ws.websockets") as mock_ws:
            mock_conn = AsyncMock()
            mock_ws.connect = AsyncMock(return_value=mock_conn)

            await ws_client.subscribe_klines(["BTCUSDT"], "5m", callback)

            expected_url = f"{BINANCE_WS_COMBINED}?streams=btcusdt@kline_5m"
            mock_ws.connect.assert_called_once()
            actual_url = mock_ws.connect.call_args[0][0]
            assert actual_url == expected_url

        await ws_client.disconnect()


# ======================================================================
# Tests: Ticker subscription
# ======================================================================

class TestTickerSubscription:
    """Test ticker stream subscription."""

    @pytest.mark.asyncio
    async def test_subscribe_ticker_registers_callbacks(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """subscribe_ticker should register callbacks."""
        await ws_client.connect()

        callback = AsyncMock()
        with patch("adapters.exchanges.binance_ws.websockets") as mock_ws:
            mock_conn = AsyncMock()
            mock_ws.connect = AsyncMock(return_value=mock_conn)

            await ws_client.subscribe_ticker(["BTCUSDT"], callback)

            assert "btcusdt@miniTicker" in ws_client._ticker_callbacks
            assert "btcusdt@miniTicker" in ws_client._active_streams

        await ws_client.disconnect()


# ======================================================================
# Tests: User-data subscription
# ======================================================================

class TestUserDataSubscription:
    """Test user-data stream subscription."""

    @pytest.mark.asyncio
    async def test_subscribe_user_data_without_key_skips(self) -> None:
        """subscribe_user_data without API key should skip silently."""
        client = BinanceWebSocket(api_key="")
        await client.connect()

        callback = AsyncMock()
        await client.subscribe_user_data(callback)

        # Should not have opened any user WS
        assert client._user_ws is None
        # Callback is not stored when there's no API key
        assert client._user_callback is None

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_user_data_with_key(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """subscribe_user_data should get listen key and open WS."""
        await ws_client.connect()

        callback = AsyncMock()

        with patch.object(
            ws_client, "_create_listen_key", return_value="test_listen_key_123"
        ) as mock_key:
            with patch("adapters.exchanges.binance_ws.websockets") as mock_ws:
                mock_conn = AsyncMock()
                mock_ws.connect = AsyncMock(return_value=mock_conn)

                await ws_client.subscribe_user_data(callback)

                mock_key.assert_called_once()
                assert ws_client._listen_key == "test_listen_key_123"
                assert ws_client._user_callback == callback

                expected_url = f"{BINANCE_WS_BASE}/test_listen_key_123"
                mock_ws.connect.assert_called_once()
                actual_url = mock_ws.connect.call_args[0][0]
                assert actual_url == expected_url

        await ws_client.disconnect()


# ======================================================================
# Tests: Message dispatch
# ======================================================================

class TestMessageDispatch:
    """Test market-data message routing."""

    @pytest.mark.asyncio
    async def test_dispatch_kline_message(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """Kline messages should be dispatched to the registered callback."""
        callback = AsyncMock()
        ws_client._kline_callbacks["btcusdt@kline_1m"] = callback

        payload = {
            "e": "kline",
            "E": 1672531200000,
            "s": "BTCUSDT",
            "k": {
                "t": 1672531200000,
                "T": 1672531259999,
                "s": "BTCUSDT",
                "i": "1m",
                "o": "42000.00",
                "h": "42100.00",
                "l": "41900.00",
                "c": "42050.00",
                "v": "10.5",
                "x": False,
            },
        }

        await ws_client._dispatch_market_message("btcusdt@kline_1m", payload)

        callback.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_dispatch_ticker_message(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """Ticker messages should be dispatched to the registered callback."""
        callback = AsyncMock()
        ws_client._ticker_callbacks["btcusdt@miniTicker"] = callback

        payload = {
            "e": "24hrMiniTicker",
            "s": "BTCUSDT",
            "c": "42000.00",
            "o": "41500.00",
            "h": "42500.00",
            "l": "41000.00",
            "v": "1000.5",
        }

        await ws_client._dispatch_market_message("btcusdt@miniTicker", payload)

        callback.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_dispatch_unknown_stream_ignored(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """Unknown stream names should not raise."""
        payload = {"e": "unknown_event"}
        # Should not raise
        await ws_client._dispatch_market_message("unknown@stream", payload)


# ======================================================================
# Tests: Kline parsing
# ======================================================================

class TestKlineParsing:
    """Test kline event parsing."""

    def test_parse_kline_event_passes_through(self) -> None:
        """_parse_kline_event should return the payload as-is."""
        payload = {
            "e": "kline",
            "s": "BTCUSDT",
            "k": {
                "t": 1672531200000,
                "s": "BTCUSDT",
                "o": "42000.00",
                "h": "42100.00",
                "l": "41900.00",
                "c": "42050.00",
                "v": "10.5",
                "i": "1m",
                "x": True,
            },
        }
        result = BinanceWebSocket._parse_kline_event(payload)
        assert result is payload
        assert result["k"]["s"] == "BTCUSDT"


# ======================================================================
# Tests: Listen key management
# ======================================================================

class TestListenKeyManagement:
    """Test listen key creation and keepalive."""

    @pytest.mark.asyncio
    async def test_create_listen_key_success(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_create_listen_key should return key on success."""
        await ws_client.connect()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"listenKey": "abc123"})

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.__aexit__ = AsyncMock(return_value=False)

        ws_client._http_session.post = MagicMock(return_value=mock_post)

        key = await ws_client._create_listen_key()
        assert key == "abc123"

        await ws_client.disconnect()

    @pytest.mark.asyncio
    async def test_create_listen_key_failure(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_create_listen_key should return None on HTTP error."""
        await ws_client.connect()

        mock_resp = AsyncMock()
        mock_resp.status = 403
        mock_resp.text = AsyncMock(return_value="Forbidden")

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.__aexit__ = AsyncMock(return_value=False)

        ws_client._http_session.post = MagicMock(return_value=mock_post)

        key = await ws_client._create_listen_key()
        assert key is None

        await ws_client.disconnect()

    @pytest.mark.asyncio
    async def test_create_listen_key_exception(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_create_listen_key should return None on network error."""
        await ws_client.connect()

        ws_client._http_session.post = MagicMock(
            side_effect=Exception("Network error")
        )

        key = await ws_client._create_listen_key()
        assert key is None

        await ws_client.disconnect()


# ======================================================================
# Tests: Reconnection
# ======================================================================

class TestReconnection:
    """Test reconnection logic."""

    @pytest.mark.asyncio
    async def test_reconnect_market_retries(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_reconnect should retry up to max_reconnect_attempts."""
        ws_client._running = True
        ws_client._active_streams = ["btcusdt@kline_1m"]

        call_count = 0

        async def failing_open(streams: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            raise Exception("Connection failed")

        ws_client._open_market_stream = failing_open

        await ws_client._reconnect("market")

        assert call_count == ws_client._max_reconnect_attempts

    @pytest.mark.asyncio
    async def test_reconnect_stops_when_not_running(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_reconnect should stop if _running is set to False."""
        ws_client._running = False
        ws_client._active_streams = ["btcusdt@kline_1m"]

        call_count = 0

        async def failing_open(streams: list[str]) -> None:
            nonlocal call_count
            call_count += 1

        ws_client._open_market_stream = failing_open

        await ws_client._reconnect("market")

        assert call_count == 0

    @pytest.mark.asyncio
    async def test_reconnect_success_resets_counter(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """Successful reconnect should reset the reconnect count."""
        ws_client._running = True
        ws_client._active_streams = ["btcusdt@kline_1m"]
        ws_client._reconnect_count["market"] = 5

        async def success_open(streams: list[str]) -> None:
            pass

        ws_client._open_market_stream = success_open

        await ws_client._reconnect("market")

        assert ws_client._reconnect_count["market"] == 0


# ======================================================================
# Tests: REST stubs raise NotImplementedError
# ======================================================================

class TestRESTStubs:
    """REST methods should raise NotImplementedError."""

    @pytest.mark.asyncio
    async def test_get_historical_klines_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.get_historical_klines("BTCUSDT", "1m")

    @pytest.mark.asyncio
    async def test_place_order_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.place_order("BTCUSDT", "BUY", 0.001)

    @pytest.mark.asyncio
    async def test_cancel_order_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.cancel_order("BTCUSDT", "123")

    @pytest.mark.asyncio
    async def test_get_balance_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.get_balance("USDT")

    @pytest.mark.asyncio
    async def test_get_all_balances_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.get_all_balances()

    @pytest.mark.asyncio
    async def test_set_stop_loss_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.set_stop_loss("BTCUSDT", 0.001, 40000.0)

    @pytest.mark.asyncio
    async def test_get_exchange_info_raises(
        self, ws_client: BinanceWebSocket
    ) -> None:
        with pytest.raises(NotImplementedError):
            await ws_client.get_exchange_info("BTCUSDT")


# ======================================================================
# Tests: Integration-style (mock WS messages)
# ======================================================================

class TestMarketStreamReading:
    """Test the market stream reader with mocked WS."""

    @pytest.mark.asyncio
    async def test_read_market_stream_dispatches_kline(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_read_market_stream should parse and dispatch kline messages."""
        ws_client._running = True

        kline_msg = json.dumps({
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "s": "BTCUSDT",
                "k": {
                    "t": 1672531200000,
                    "o": "42000.00",
                    "h": "42100.00",
                    "l": "41900.00",
                    "c": "42050.00",
                    "v": "10.5",
                    "i": "1m",
                    "x": True,
                    "s": "BTCUSDT",
                },
            },
        })

        callback = AsyncMock()
        ws_client._kline_callbacks["btcusdt@kline_1m"] = callback

        # Mock WS that sends one message then closes
        recv_count = 0

        async def mock_recv():
            nonlocal recv_count
            recv_count += 1
            if recv_count == 1:
                return kline_msg
            # Stop after first message
            ws_client._running = False
            raise websockets.ConnectionClosed(None, None)

        import websockets

        mock_ws = AsyncMock()
        mock_ws.recv = mock_recv
        mock_ws.close = AsyncMock()
        ws_client._market_ws = mock_ws

        # Suppress reconnection by setting running to False after dispatch
        original_reconnect = ws_client._reconnect

        async def no_reconnect(stream_type: str) -> None:
            pass

        ws_client._reconnect = no_reconnect

        await ws_client._read_market_stream()

        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["e"] == "kline"
        assert call_args["k"]["c"] == "42050.00"

    @pytest.mark.asyncio
    async def test_read_user_stream_dispatches(
        self, ws_client: BinanceWebSocket
    ) -> None:
        """_read_user_stream should dispatch events to user callback."""
        ws_client._running = True

        user_msg = json.dumps({
            "e": "executionReport",
            "s": "BTCUSDT",
            "S": "BUY",
            "X": "FILLED",
            "z": "0.001",
            "L": "42000.00",
        })

        callback = AsyncMock()
        ws_client._user_callback = callback

        recv_count = 0

        async def mock_recv():
            nonlocal recv_count
            recv_count += 1
            if recv_count == 1:
                return user_msg
            ws_client._running = False
            raise websockets.ConnectionClosed(None, None)

        import websockets

        mock_ws = AsyncMock()
        mock_ws.recv = mock_recv
        mock_ws.close = AsyncMock()
        ws_client._user_ws = mock_ws

        async def no_reconnect(stream_type: str) -> None:
            pass

        ws_client._reconnect = no_reconnect

        await ws_client._read_user_stream()

        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["e"] == "executionReport"
        assert call_args["X"] == "FILLED"
