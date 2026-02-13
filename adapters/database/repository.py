"""Database repository interfaces and implementations.

Defines the abstract BaseRepository that the engine depends on, plus
a concrete PostgresRepository backed by SQLAlchemy 2.0 async sessions.
Also provides a Database class for connection pool management.

Dependencies: sqlalchemy[asyncio], asyncpg
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from adapters.database.models import (
    AIReport,
    Alert,
    Backtest,
    Base,
    DailyStat,
    Notification,
    Pair,
    Strategy,
    Trade,
    TradeJournal,
    User,
)

logger = logging.getLogger(__name__)


# ======================================================================
# Database connection pool manager
# ======================================================================

class Database:
    """Async database connection manager.

    Manages the SQLAlchemy async engine and session factory.
    Provides a context manager for obtaining sessions.

    Parameters
    ----------
    database_url : str
        SQLAlchemy async database URL,
        e.g. "postgresql+asyncpg://user:pass@localhost/dbname".
    echo : bool
        If True, log all SQL statements (debug only).
    pool_size : int
        Connection pool size.
    max_overflow : int
        Max number of connections beyond pool_size.
    """

    def __init__(
        self,
        database_url: str = "",
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
    ) -> None:
        self._database_url = database_url
        self._echo = echo
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self, database_url: str | None = None) -> None:
        """Create the engine and session factory, then create tables.

        Parameters
        ----------
        database_url : str | None
            Override the URL passed to __init__.
        """
        url = database_url or self._database_url
        if not url:
            raise ValueError("No database_url provided")

        # Handle SQLite for testing (no pool settings)
        if "sqlite" in url:
            self._engine = create_async_engine(url, echo=self._echo)
        else:
            self._engine = create_async_engine(
                url,
                echo=self._echo,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                pool_pre_ping=True,
            )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create tables (dev/test; use Alembic in production)
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info(
            "Database connected: %s",
            url.split("@")[-1] if "@" in url else url,
        )

    async def disconnect(self) -> None:
        """Close the engine and release all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database disconnected")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide an async session with auto commit/rollback.

        Yields
        ------
        AsyncSession
            An active database session.
        """
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the session factory for direct use."""
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._session_factory


# ======================================================================
# Abstract repository interface
# ======================================================================

class BaseRepository(ABC):
    """Abstract repository interface.

    The engine and API layers depend only on this interface.
    Concrete implementations handle the actual database I/O.
    """

    @abstractmethod
    async def save_trade(self, trade: dict[str, Any]) -> str: ...

    @abstractmethod
    async def get_trades(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def save_strategy(self, strategy: dict[str, Any]) -> str: ...

    @abstractmethod
    async def get_active_strategy(
        self, pair: str | None = None
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    async def save_daily_stats(self, stats: dict[str, Any]) -> None: ...

    @abstractmethod
    async def get_user(self, username: str) -> dict[str, Any] | None: ...


# ======================================================================
# Helper: ORM model to dict
# ======================================================================

def _to_dict(obj: Any) -> dict[str, Any]:
    """Convert an ORM model instance to a plain dictionary."""
    result: dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            result[col.name] = val.isoformat()
        elif isinstance(val, date):
            result[col.name] = val.isoformat()
        else:
            result[col.name] = val
    return result


# ======================================================================
# Concrete PostgreSQL repository
# ======================================================================

class PostgresRepository(BaseRepository):
    """PostgreSQL implementation using SQLAlchemy 2.0 async sessions.

    Parameters
    ----------
    database : Database
        An initialized Database instance with an active connection pool.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    # ==================================================================
    # Users
    # ==================================================================

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        username: str,
    ) -> dict[str, Any]:
        """Create a new user.

        Parameters
        ----------
        email : str
            User email address.
        hashed_password : str
            Pre-hashed password.
        username : str
            Unique username.

        Returns
        -------
        dict
            The created user record.
        """
        async with self._db.session() as session:
            user = User(
                email=email,
                hashed_password=hashed_password,
                username=username,
            )
            session.add(user)
            await session.flush()
            return _to_dict(user)

    async def get_user(self, username: str) -> dict[str, Any] | None:
        """Fetch user by username.

        Parameters
        ----------
        username : str
            The username to look up.

        Returns
        -------
        dict | None
            User data or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return _to_dict(user) if user else None

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch user by email.

        Parameters
        ----------
        email : str
            The email to look up.

        Returns
        -------
        dict | None
            User data or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return _to_dict(user) if user else None

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user by ID.

        Parameters
        ----------
        user_id : str
            The user UUID.

        Returns
        -------
        dict | None
            User data or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return _to_dict(user) if user else None

    async def update_user(
        self, user_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Update user fields.

        Parameters
        ----------
        user_id : str
            The user UUID.
        **kwargs
            Fields to update.

        Returns
        -------
        dict | None
            Updated user data, or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                return None
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            await session.flush()
            await session.refresh(user)
            return _to_dict(user)

    # ==================================================================
    # Trades
    # ==================================================================

    async def save_trade(self, trade_data: dict[str, Any]) -> str:
        """Persist a completed trade.

        Parameters
        ----------
        trade_data : dict
            Trade data matching the Trade model fields.

        Returns
        -------
        str
            The ID of the saved trade.
        """
        async with self._db.session() as session:
            data = dict(trade_data)
            # Handle metadata serialization
            if "metadata" in data:
                data["metadata_json"] = json.dumps(data.pop("metadata"))
            trade = Trade(**data)
            session.add(trade)
            await session.flush()
            return trade.id

    async def get_trades(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query trades with optional filters.

        Parameters
        ----------
        filters : dict | None
            Optional filters: pair, strategy_name, status,
            date_from, date_to, limit, offset.

        Returns
        -------
        list[dict]
            List of trade records.
        """
        filters = filters or {}
        async with self._db.session() as session:
            stmt = select(Trade)

            conditions = []
            if "pair" in filters:
                conditions.append(Trade.pair == filters["pair"])
            if "strategy_name" in filters:
                conditions.append(
                    Trade.strategy_name == filters["strategy_name"]
                )
            if "status" in filters:
                conditions.append(Trade.status == filters["status"])
            if "date_from" in filters:
                conditions.append(Trade.entry_time >= filters["date_from"])
            if "date_to" in filters:
                conditions.append(Trade.entry_time <= filters["date_to"])

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.order_by(Trade.entry_time.desc())

            if "limit" in filters:
                stmt = stmt.limit(filters["limit"])
            if "offset" in filters:
                stmt = stmt.offset(filters["offset"])

            result = await session.execute(stmt)
            trades = result.scalars().all()
            return [_to_dict(t) for t in trades]

    async def get_trade_by_id(
        self, trade_id: str
    ) -> dict[str, Any] | None:
        """Fetch a single trade by ID.

        Parameters
        ----------
        trade_id : str
            The trade UUID.

        Returns
        -------
        dict | None
            Trade data or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(Trade).where(Trade.id == trade_id)
            result = await session.execute(stmt)
            trade = result.scalar_one_or_none()
            return _to_dict(trade) if trade else None

    async def get_trade_stats(
        self,
        user_id: str | None = None,
        period: str = "all",
    ) -> dict[str, Any]:
        """Compute trade statistics.

        Parameters
        ----------
        user_id : str | None
            Reserved for future per-user filtering.
        period : str
            "all", "today", "week", "month".

        Returns
        -------
        dict
            Statistics: total_trades, winning_trades, losing_trades,
            win_rate, total_pnl, avg_pnl, max_win, max_loss.
        """
        async with self._db.session() as session:
            stmt = select(Trade).where(Trade.status == "CLOSED")

            if period == "today":
                today_start = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                stmt = stmt.where(Trade.entry_time >= today_start)
            elif period == "week":
                stmt = stmt.where(
                    Trade.entry_time >= datetime.utcnow() - timedelta(days=7)
                )
            elif period == "month":
                stmt = stmt.where(
                    Trade.entry_time >= datetime.utcnow() - timedelta(days=30)
                )

            result = await session.execute(stmt)
            trades = result.scalars().all()

            if not trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0,
                    "max_win": 0.0,
                    "max_loss": 0.0,
                }

            total = len(trades)
            winners = [t for t in trades if t.pnl_usdt > 0]
            losers = [t for t in trades if t.pnl_usdt <= 0]
            pnls = [t.pnl_usdt for t in trades]

            return {
                "total_trades": total,
                "winning_trades": len(winners),
                "losing_trades": len(losers),
                "win_rate": (len(winners) / total * 100) if total else 0.0,
                "total_pnl": sum(pnls),
                "avg_pnl": sum(pnls) / total if total else 0.0,
                "max_win": max(pnls) if pnls else 0.0,
                "max_loss": min(pnls) if pnls else 0.0,
            }

    async def update_trade(
        self, trade_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Update trade fields.

        Parameters
        ----------
        trade_id : str
            The trade UUID.
        **kwargs
            Fields to update.

        Returns
        -------
        dict | None
            Updated trade data, or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(Trade).where(Trade.id == trade_id)
            result = await session.execute(stmt)
            trade = result.scalar_one_or_none()
            if trade is None:
                return None
            if "metadata" in kwargs:
                kwargs["metadata_json"] = json.dumps(kwargs.pop("metadata"))
            for key, value in kwargs.items():
                if hasattr(trade, key):
                    setattr(trade, key, value)
            await session.flush()
            await session.refresh(trade)
            return _to_dict(trade)

    # ==================================================================
    # Strategies
    # ==================================================================

    async def save_strategy(self, strategy_data: dict[str, Any]) -> str:
        """Create a new strategy.

        Parameters
        ----------
        strategy_data : dict
            Strategy data matching the Strategy model fields.

        Returns
        -------
        str
            The ID of the saved strategy.
        """
        async with self._db.session() as session:
            strategy = Strategy(**strategy_data)
            session.add(strategy)
            await session.flush()
            return strategy.id

    async def get_strategies(
        self, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all strategies, optionally filtered by creator.

        Parameters
        ----------
        user_id : str | None
            Filter by created_by field.

        Returns
        -------
        list[dict]
            List of strategy records.
        """
        async with self._db.session() as session:
            stmt = select(Strategy)
            if user_id:
                stmt = stmt.where(Strategy.created_by == user_id)
            stmt = stmt.order_by(Strategy.created_at.desc())
            result = await session.execute(stmt)
            strategies = result.scalars().all()
            return [_to_dict(s) for s in strategies]

    async def get_active_strategy(
        self, pair: str | None = None
    ) -> dict[str, Any] | None:
        """Get the currently active strategy.

        Parameters
        ----------
        pair : str | None
            Optional pair filter (checks json_definition content).

        Returns
        -------
        dict | None
            Active strategy data or None.
        """
        async with self._db.session() as session:
            stmt = select(Strategy).where(Strategy.is_active == True)  # noqa: E712
            if pair:
                stmt = stmt.where(
                    Strategy.json_definition.contains(pair)
                )
            stmt = stmt.limit(1)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            return _to_dict(strategy) if strategy else None

    async def update_strategy(
        self, strategy_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Update strategy fields.

        Parameters
        ----------
        strategy_id : str
            The strategy UUID.
        **kwargs
            Fields to update.

        Returns
        -------
        dict | None
            Updated strategy data, or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(Strategy).where(Strategy.id == strategy_id)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            if strategy is None:
                return None
            for key, value in kwargs.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)
            await session.flush()
            await session.refresh(strategy)
            return _to_dict(strategy)

    async def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy by ID.

        Parameters
        ----------
        strategy_id : str
            The strategy UUID.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        async with self._db.session() as session:
            stmt = select(Strategy).where(Strategy.id == strategy_id)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            if strategy is None:
                return False
            await session.delete(strategy)
            return True

    # ==================================================================
    # Pairs
    # ==================================================================

    async def create_pair(self, pair_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new trading pair record.

        Parameters
        ----------
        pair_data : dict
            Pair data matching the Pair model fields.

        Returns
        -------
        dict
            The created pair record.
        """
        async with self._db.session() as session:
            pair = Pair(**pair_data)
            session.add(pair)
            await session.flush()
            return _to_dict(pair)

    async def get_active_pairs(self) -> list[dict[str, Any]]:
        """Get all active trading pairs.

        Returns
        -------
        list[dict]
            List of active pair records.
        """
        async with self._db.session() as session:
            stmt = select(Pair).where(Pair.is_active == True)  # noqa: E712
            result = await session.execute(stmt)
            pairs = result.scalars().all()
            return [_to_dict(p) for p in pairs]

    async def update_pair(
        self, pair_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Update pair fields.

        Parameters
        ----------
        pair_id : str
            The pair UUID.
        **kwargs
            Fields to update.

        Returns
        -------
        dict | None
            Updated pair data, or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(Pair).where(Pair.id == pair_id)
            result = await session.execute(stmt)
            pair = result.scalar_one_or_none()
            if pair is None:
                return None
            for key, value in kwargs.items():
                if hasattr(pair, key):
                    setattr(pair, key, value)
            await session.flush()
            await session.refresh(pair)
            return _to_dict(pair)

    # ==================================================================
    # Daily Stats
    # ==================================================================

    async def save_daily_stats(self, stats: dict[str, Any]) -> None:
        """Persist daily trading statistics.

        Maps keys from engine/portfolio stats to DailyStat model columns.
        """
        mapped = {
            "date": stats.get("date", datetime.now(timezone.utc).date().isoformat()),
            "pair": stats.get("pair", "ALL"),
            "total_trades": stats.get("total_trades", 0),
            "winning_trades": stats.get("wins", stats.get("winning_trades", 0)),
            "pnl_usdt": stats.get("total_pnl", stats.get("pnl_usdt", 0.0)),
            "max_drawdown": stats.get("max_drawdown", 0.0),
            "strategy_name": stats.get("strategy_name", ""),
        }
        async with self._db.session() as session:
            stat = DailyStat(**mapped)
            session.add(stat)

    async def create_daily_stat(
        self, stat_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new daily stat record.

        Parameters
        ----------
        stat_data : dict
            Stats data matching the DailyStat model fields.

        Returns
        -------
        dict
            The created daily stat record.
        """
        async with self._db.session() as session:
            stat = DailyStat(**stat_data)
            session.add(stat)
            await session.flush()
            return _to_dict(stat)

    async def get_daily_stats(
        self,
        user_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily stats within a date range.

        Parameters
        ----------
        user_id : str | None
            Reserved for future per-user stats.
        start_date : date | None
            Start of the date range (inclusive).
        end_date : date | None
            End of the date range (inclusive).

        Returns
        -------
        list[dict]
            List of daily stat records.
        """
        async with self._db.session() as session:
            stmt = select(DailyStat)
            conditions = []
            if start_date:
                conditions.append(DailyStat.date >= start_date)
            if end_date:
                conditions.append(DailyStat.date <= end_date)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            stmt = stmt.order_by(DailyStat.date.desc())
            result = await session.execute(stmt)
            stats = result.scalars().all()
            return [_to_dict(s) for s in stats]

    # ==================================================================
    # Alerts
    # ==================================================================

    async def create_alert(
        self, alert_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new alert.

        Parameters
        ----------
        alert_data : dict
            Alert data matching the Alert model fields.

        Returns
        -------
        dict
            The created alert record.
        """
        async with self._db.session() as session:
            alert = Alert(**alert_data)
            session.add(alert)
            await session.flush()
            return _to_dict(alert)

    async def get_alerts(
        self,
        user_id: str,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Get alerts for a user.

        Parameters
        ----------
        user_id : str
            The user UUID.
        active_only : bool
            If True, return only active alerts.

        Returns
        -------
        list[dict]
            List of alert records.
        """
        async with self._db.session() as session:
            stmt = select(Alert).where(Alert.user_id == user_id)
            if active_only:
                stmt = stmt.where(Alert.is_active == True)  # noqa: E712
            stmt = stmt.order_by(Alert.created_at.desc())
            result = await session.execute(stmt)
            alerts = result.scalars().all()
            return [_to_dict(a) for a in alerts]

    async def update_alert(
        self, alert_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Update alert fields.

        Parameters
        ----------
        alert_id : str
            The alert UUID.
        **kwargs
            Fields to update.

        Returns
        -------
        dict | None
            Updated alert data, or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(Alert).where(Alert.id == alert_id)
            result = await session.execute(stmt)
            alert = result.scalar_one_or_none()
            if alert is None:
                return None
            for key, value in kwargs.items():
                if hasattr(alert, key):
                    setattr(alert, key, value)
            await session.flush()
            await session.refresh(alert)
            return _to_dict(alert)

    async def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert by ID.

        Parameters
        ----------
        alert_id : str
            The alert UUID.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        async with self._db.session() as session:
            stmt = select(Alert).where(Alert.id == alert_id)
            result = await session.execute(stmt)
            alert = result.scalar_one_or_none()
            if alert is None:
                return False
            await session.delete(alert)
            return True

    # ==================================================================
    # AI Reports
    # ==================================================================

    async def create_ai_report(
        self, report_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new AI report.

        Parameters
        ----------
        report_data : dict
            Report data matching the AIReport model fields.

        Returns
        -------
        dict
            The created report record.
        """
        async with self._db.session() as session:
            report = AIReport(**report_data)
            session.add(report)
            await session.flush()
            return _to_dict(report)

    async def get_ai_reports(
        self,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get AI reports, optionally filtered by type.

        Parameters
        ----------
        report_type : str | None
            Filter by report type (daily, weekly, custom).
        limit : int
            Maximum number of reports to return.

        Returns
        -------
        list[dict]
            List of report records.
        """
        async with self._db.session() as session:
            stmt = select(AIReport)
            if report_type:
                stmt = stmt.where(AIReport.report_type == report_type)
            stmt = stmt.order_by(AIReport.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            reports = result.scalars().all()
            return [_to_dict(r) for r in reports]

    async def get_ai_report_by_id(
        self, report_id: str
    ) -> dict[str, Any] | None:
        """Fetch an AI report by ID.

        Parameters
        ----------
        report_id : str
            The report UUID.

        Returns
        -------
        dict | None
            Report data or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(AIReport).where(AIReport.id == report_id)
            result = await session.execute(stmt)
            report = result.scalar_one_or_none()
            return _to_dict(report) if report else None

    # ==================================================================
    # Backtests
    # ==================================================================

    async def create_backtest(
        self, backtest_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new backtest record.

        Parameters
        ----------
        backtest_data : dict
            Backtest data matching the Backtest model fields.

        Returns
        -------
        dict
            The created backtest record.
        """
        async with self._db.session() as session:
            backtest = Backtest(**backtest_data)
            session.add(backtest)
            await session.flush()
            return _to_dict(backtest)

    async def get_backtests(
        self,
        strategy_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get backtest records, optionally filtered by strategy.

        Parameters
        ----------
        strategy_id : str | None
            Filter by strategy ID.
        limit : int
            Maximum number of records to return.

        Returns
        -------
        list[dict]
            List of backtest records.
        """
        async with self._db.session() as session:
            stmt = select(Backtest)
            if strategy_id:
                stmt = stmt.where(Backtest.strategy_id == strategy_id)
            stmt = stmt.order_by(Backtest.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            backtests = result.scalars().all()
            return [_to_dict(b) for b in backtests]

    async def get_backtest_by_id(
        self, backtest_id: str
    ) -> dict[str, Any] | None:
        """Fetch a backtest by ID.

        Parameters
        ----------
        backtest_id : str
            The backtest UUID.

        Returns
        -------
        dict | None
            Backtest data or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(Backtest).where(Backtest.id == backtest_id)
            result = await session.execute(stmt)
            backtest = result.scalar_one_or_none()
            return _to_dict(backtest) if backtest else None

    # ==================================================================
    # Trade Journal
    # ==================================================================

    async def create_journal_entry(
        self, entry_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new trade journal entry.

        Parameters
        ----------
        entry_data : dict
            Journal entry data matching the TradeJournal model fields.

        Returns
        -------
        dict
            The created journal entry record.
        """
        async with self._db.session() as session:
            entry = TradeJournal(**entry_data)
            session.add(entry)
            await session.flush()
            return _to_dict(entry)

    async def get_journal_entries(
        self, trade_id: str
    ) -> list[dict[str, Any]]:
        """Get journal entries for a trade.

        Parameters
        ----------
        trade_id : str
            The trade UUID.

        Returns
        -------
        list[dict]
            List of journal entry records.
        """
        async with self._db.session() as session:
            stmt = (
                select(TradeJournal)
                .where(TradeJournal.trade_id == trade_id)
                .order_by(TradeJournal.created_at.desc())
            )
            result = await session.execute(stmt)
            entries = result.scalars().all()
            return [_to_dict(e) for e in entries]

    async def update_journal_entry(
        self, entry_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Update a journal entry.

        Parameters
        ----------
        entry_id : str
            The journal entry UUID.
        **kwargs
            Fields to update.

        Returns
        -------
        dict | None
            Updated entry data, or None if not found.
        """
        async with self._db.session() as session:
            stmt = select(TradeJournal).where(TradeJournal.id == entry_id)
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            if entry is None:
                return None
            for key, value in kwargs.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            await session.flush()
            await session.refresh(entry)
            return _to_dict(entry)

    async def delete_journal_entry(self, entry_id: str) -> bool:
        """Delete a journal entry by ID.

        Parameters
        ----------
        entry_id : str
            The journal entry UUID.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        async with self._db.session() as session:
            stmt = select(TradeJournal).where(TradeJournal.id == entry_id)
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            if entry is None:
                return False
            await session.delete(entry)
            return True

    # ==================================================================
    # Notifications
    # ==================================================================

    async def create_notification(
        self, notification_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new notification.

        Parameters
        ----------
        notification_data : dict
            Notification data matching the Notification model fields.

        Returns
        -------
        dict
            The created notification record.
        """
        async with self._db.session() as session:
            notification = Notification(**notification_data)
            session.add(notification)
            await session.flush()
            return _to_dict(notification)

    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get notifications for a user.

        Parameters
        ----------
        user_id : str
            The user UUID.
        unread_only : bool
            If True, return only unread notifications.
        limit : int
            Maximum number of notifications to return.

        Returns
        -------
        list[dict]
            List of notification records.
        """
        async with self._db.session() as session:
            stmt = select(Notification).where(
                Notification.user_id == user_id
            )
            if unread_only:
                stmt = stmt.where(
                    Notification.is_read == False  # noqa: E712
                )
            stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            notifications = result.scalars().all()
            return [_to_dict(n) for n in notifications]

    async def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read.

        Parameters
        ----------
        notification_id : str
            The notification UUID.

        Returns
        -------
        bool
            True if updated, False if not found.
        """
        async with self._db.session() as session:
            stmt = select(Notification).where(
                Notification.id == notification_id
            )
            result = await session.execute(stmt)
            notification = result.scalar_one_or_none()
            if notification is None:
                return False
            notification.is_read = True
            await session.flush()
            return True

    async def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification by ID.

        Parameters
        ----------
        notification_id : str
            The notification UUID.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        async with self._db.session() as session:
            stmt = select(Notification).where(
                Notification.id == notification_id
            )
            result = await session.execute(stmt)
            notification = result.scalar_one_or_none()
            if notification is None:
                return False
            await session.delete(notification)
            return True
