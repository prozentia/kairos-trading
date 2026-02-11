"""Abstract base class for exchange adapters.

Defines the interface that all exchange implementations must follow.
This ensures the engine and other consumers are decoupled from any
specific exchange's API details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable


class BaseExchange(ABC):
    """Abstract exchange adapter.

    Every concrete exchange (Binance, Bybit, etc.) must implement all
    methods defined here.  The engine depends *only* on this interface,
    never on a concrete class.
    """

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection(s) to the exchange (REST + WS)."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close all connections."""
        ...

    # ------------------------------------------------------------------
    # Market-data streams (WebSocket)
    # ------------------------------------------------------------------

    @abstractmethod
    async def subscribe_klines(
        self,
        pairs: list[str],
        timeframe: str,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Subscribe to kline/candlestick streams for the given pairs.

        Parameters
        ----------
        pairs : list[str]
            Symbols to subscribe to, e.g. ["BTCUSDT", "ETHUSDT"].
        timeframe : str
            Kline interval, e.g. "1m", "5m", "1h".
        callback :
            Async callable invoked with each incoming kline event.
        """
        ...

    @abstractmethod
    async def subscribe_ticker(
        self,
        pairs: list[str],
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Subscribe to real-time ticker updates.

        Parameters
        ----------
        pairs : list[str]
            Symbols to subscribe to.
        callback :
            Async callable invoked with each ticker event.
        """
        ...

    @abstractmethod
    async def subscribe_user_data(
        self,
        callback: Callable[..., Awaitable[None]],
    ) -> None:
        """Subscribe to user-data stream (fills, balance updates, etc.).

        Parameters
        ----------
        callback :
            Async callable invoked for each user-data event.
        """
        ...

    # ------------------------------------------------------------------
    # Historical data (REST)
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_historical_klines(
        self,
        pair: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch historical klines via REST API.

        Returns a list of dicts with keys:
        timestamp, open, high, low, close, volume.
        """
        ...

    # ------------------------------------------------------------------
    # Order management (REST)
    # ------------------------------------------------------------------

    @abstractmethod
    async def place_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> dict[str, Any]:
        """Place an order on the exchange.

        Parameters
        ----------
        pair : str
            Trading pair, e.g. "BTCUSDT".
        side : str
            "BUY" or "SELL".
        quantity : float
            Order quantity in base asset.
        order_type : str
            "MARKET", "LIMIT", etc.
        price : float | None
            Required for LIMIT orders.

        Returns
        -------
        dict
            Exchange order response containing at least order_id and status.
        """
        ...

    @abstractmethod
    async def cancel_order(self, pair: str, order_id: str) -> bool:
        """Cancel an open order.

        Returns True if successfully cancelled.
        """
        ...

    @abstractmethod
    async def set_stop_loss(
        self,
        pair: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Place a stop-loss order.

        Returns the exchange response for the stop-loss order.
        """
        ...

    # ------------------------------------------------------------------
    # Account queries (REST)
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_balance(self, asset: str) -> float:
        """Get free balance for a single asset.

        Parameters
        ----------
        asset : str
            Asset symbol, e.g. "USDT", "BTC".

        Returns
        -------
        float
            Available (free) balance.
        """
        ...

    @abstractmethod
    async def get_all_balances(self) -> dict[str, float]:
        """Get free balances for all non-zero assets.

        Returns
        -------
        dict[str, float]
            Mapping of asset symbol to free balance.
        """
        ...

    # ------------------------------------------------------------------
    # Exchange metadata (REST)
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_exchange_info(self, pair: str) -> dict[str, Any]:
        """Fetch trading rules for a pair (lot size, tick size, etc.).

        Returns
        -------
        dict
            Contains at minimum: min_qty, step_size, tick_size, min_notional.
        """
        ...
