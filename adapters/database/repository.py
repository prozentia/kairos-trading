"""Database repository interfaces and implementations.

Defines the abstract BaseRepository that the engine depends on, plus
a concrete PostgresRepository backed by SQLAlchemy 2.0 async sessions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """Abstract repository interface.

    The engine and API layers depend only on this interface.
    Concrete implementations handle the actual database I/O.
    """

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    @abstractmethod
    async def save_trade(self, trade: dict[str, Any]) -> str:
        """Persist a completed trade.

        Parameters
        ----------
        trade : dict
            Trade data matching the Trade model fields.

        Returns
        -------
        str
            The ID of the saved trade.
        """
        ...

    @abstractmethod
    async def get_trades(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve trades matching optional filters.

        Parameters
        ----------
        filters : dict | None
            Optional filters: pair, strategy_name, date_from, date_to,
            limit, offset.

        Returns
        -------
        list[dict]
            List of trade records.
        """
        ...

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    @abstractmethod
    async def save_strategy(self, strategy: dict[str, Any]) -> str:
        """Create or update a strategy definition.

        Returns
        -------
        str
            The ID of the saved strategy.
        """
        ...

    @abstractmethod
    async def get_active_strategy(self, pair: str) -> dict[str, Any] | None:
        """Get the currently active strategy for a trading pair.

        Parameters
        ----------
        pair : str
            Trading pair symbol, e.g. "BTCUSDT".

        Returns
        -------
        dict | None
            Strategy definition or None if no active strategy.
        """
        ...

    # ------------------------------------------------------------------
    # Daily stats
    # ------------------------------------------------------------------

    @abstractmethod
    async def save_daily_stats(self, stats: dict[str, Any]) -> None:
        """Persist daily trading statistics.

        Parameters
        ----------
        stats : dict
            Daily stats data matching the DailyStat model fields.
        """
        ...

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_user(self, username: str) -> dict[str, Any] | None:
        """Retrieve a user by username.

        Parameters
        ----------
        username : str
            The username to look up.

        Returns
        -------
        dict | None
            User data or None if not found.
        """
        ...


class PostgresRepository(BaseRepository):
    """PostgreSQL implementation using SQLAlchemy 2.0 async sessions.

    Requires an async engine and session factory to be injected
    at construction time.
    """

    def __init__(self, session_factory: Any) -> None:
        """Initialize with an async session factory.

        Parameters
        ----------
        session_factory :
            An async_sessionmaker instance from SQLAlchemy.
        """
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    async def save_trade(self, trade: dict[str, Any]) -> str:
        """Save a trade to PostgreSQL."""
        raise NotImplementedError("PostgresRepository.save_trade() not yet implemented")

    async def get_trades(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query trades with optional filters."""
        raise NotImplementedError("PostgresRepository.get_trades() not yet implemented")

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    async def save_strategy(self, strategy: dict[str, Any]) -> str:
        """Upsert a strategy definition."""
        raise NotImplementedError("PostgresRepository.save_strategy() not yet implemented")

    async def get_active_strategy(self, pair: str) -> dict[str, Any] | None:
        """Get active strategy for a pair."""
        raise NotImplementedError("PostgresRepository.get_active_strategy() not yet implemented")

    # ------------------------------------------------------------------
    # Daily stats
    # ------------------------------------------------------------------

    async def save_daily_stats(self, stats: dict[str, Any]) -> None:
        """Insert daily stats row."""
        raise NotImplementedError("PostgresRepository.save_daily_stats() not yet implemented")

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def get_user(self, username: str) -> dict[str, Any] | None:
        """Fetch user by username."""
        raise NotImplementedError("PostgresRepository.get_user() not yet implemented")
