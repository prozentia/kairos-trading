"""Unit tests for the PostgresRepository adapter.

Uses SQLite in-memory (via aiosqlite) for fast, isolated testing
without requiring a running PostgreSQL instance.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio

from adapters.database.repository import Database, PostgresRepository


# ======================================================================
# Fixtures
# ======================================================================

@pytest_asyncio.fixture
async def database():
    """Create an in-memory SQLite database for testing."""
    db = Database(database_url="sqlite+aiosqlite:///:memory:")
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def repo(database: Database) -> PostgresRepository:
    """Create a repository backed by the in-memory database."""
    return PostgresRepository(database)


# ======================================================================
# Tests: Database lifecycle
# ======================================================================

class TestDatabaseLifecycle:
    """Test Database connection and session management."""

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self) -> None:
        """Database should connect and disconnect cleanly."""
        db = Database(database_url="sqlite+aiosqlite:///:memory:")
        await db.connect()
        assert db._engine is not None
        assert db._session_factory is not None

        await db.disconnect()
        assert db._engine is None
        assert db._session_factory is None

    @pytest.mark.asyncio
    async def test_connect_without_url_raises(self) -> None:
        """Connecting without a URL should raise ValueError."""
        db = Database()
        with pytest.raises(ValueError, match="No database_url"):
            await db.connect()

    @pytest.mark.asyncio
    async def test_session_without_connect_raises(self) -> None:
        """Using session before connect should raise RuntimeError."""
        db = Database()
        with pytest.raises(RuntimeError, match="not connected"):
            async with db.session():
                pass

    @pytest.mark.asyncio
    async def test_session_factory_without_connect_raises(self) -> None:
        """Accessing session_factory before connect should raise."""
        db = Database()
        with pytest.raises(RuntimeError, match="not connected"):
            _ = db.session_factory


# ======================================================================
# Tests: Users
# ======================================================================

class TestUsers:
    """Test user CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, repo: PostgresRepository) -> None:
        """create_user should return a dict with all user fields."""
        user = await repo.create_user(
            email="test@example.com",
            hashed_password="hashed_123",
            username="testuser",
        )

        assert user["email"] == "test@example.com"
        assert user["username"] == "testuser"
        assert user["hashed_password"] == "hashed_123"
        assert user["is_active"] is True
        assert user["id"] is not None

    @pytest.mark.asyncio
    async def test_get_user_by_username(
        self, repo: PostgresRepository
    ) -> None:
        """get_user should find a user by username."""
        await repo.create_user(
            email="find@example.com",
            hashed_password="hash",
            username="findme",
        )

        user = await repo.get_user("findme")

        assert user is not None
        assert user["username"] == "findme"
        assert user["email"] == "find@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self, repo: PostgresRepository
    ) -> None:
        """get_user should return None for non-existent username."""
        user = await repo.get_user("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(
        self, repo: PostgresRepository
    ) -> None:
        """get_user_by_email should find a user by email."""
        await repo.create_user(
            email="email@example.com",
            hashed_password="hash",
            username="emailuser",
        )

        user = await repo.get_user_by_email("email@example.com")

        assert user is not None
        assert user["email"] == "email@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(
        self, repo: PostgresRepository
    ) -> None:
        """get_user_by_email should return None for unknown email."""
        user = await repo.get_user_by_email("nope@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self, repo: PostgresRepository
    ) -> None:
        """get_user_by_id should find a user by UUID."""
        created = await repo.create_user(
            email="id@example.com",
            hashed_password="hash",
            username="iduser",
        )

        user = await repo.get_user_by_id(created["id"])

        assert user is not None
        assert user["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_update_user(self, repo: PostgresRepository) -> None:
        """update_user should modify specified fields."""
        created = await repo.create_user(
            email="update@example.com",
            hashed_password="hash",
            username="updateuser",
        )

        updated = await repo.update_user(
            created["id"], is_active=False
        )

        assert updated is not None
        assert updated["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, repo: PostgresRepository
    ) -> None:
        """update_user should return None for non-existent user."""
        result = await repo.update_user("nonexistent-id", is_active=False)
        assert result is None


# ======================================================================
# Tests: Trades
# ======================================================================

class TestTrades:
    """Test trade CRUD and statistics."""

    @pytest.mark.asyncio
    async def test_save_trade(self, repo: PostgresRepository) -> None:
        """save_trade should persist a trade and return its ID."""
        trade_data = {
            "pair": "BTCUSDT",
            "side": "BUY",
            "entry_price": 45000.0,
            "exit_price": 46000.0,
            "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "exit_time": datetime(2024, 1, 15, 12, 0, 0),
            "pnl_usdt": 1.0,
            "pnl_pct": 2.22,
            "fees": 0.05,
            "strategy_name": "test_strategy",
            "status": "CLOSED",
        }

        trade_id = await repo.save_trade(trade_data)

        assert trade_id is not None
        assert isinstance(trade_id, str)

    @pytest.mark.asyncio
    async def test_get_trades_no_filters(
        self, repo: PostgresRepository
    ) -> None:
        """get_trades without filters should return all trades."""
        for i in range(3):
            await repo.save_trade({
                "pair": "BTCUSDT",
                "side": "BUY",
                "entry_price": 45000.0 + i * 100,
                "quantity": 0.001,
                "entry_time": datetime(2024, 1, 15, 10 + i, 0, 0),
                "status": "CLOSED",
            })

        trades = await repo.get_trades()

        assert len(trades) == 3

    @pytest.mark.asyncio
    async def test_get_trades_with_pair_filter(
        self, repo: PostgresRepository
    ) -> None:
        """get_trades with pair filter should return matching trades."""
        await repo.save_trade({
            "pair": "BTCUSDT",
            "side": "BUY",
            "entry_price": 45000.0,
            "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "CLOSED",
        })
        await repo.save_trade({
            "pair": "ETHUSDT",
            "side": "BUY",
            "entry_price": 2500.0,
            "quantity": 0.1,
            "entry_time": datetime(2024, 1, 15, 11, 0, 0),
            "status": "CLOSED",
        })

        trades = await repo.get_trades(filters={"pair": "BTCUSDT"})

        assert len(trades) == 1
        assert trades[0]["pair"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_trades_with_limit_and_offset(
        self, repo: PostgresRepository
    ) -> None:
        """get_trades should support pagination."""
        for i in range(5):
            await repo.save_trade({
                "pair": "BTCUSDT",
                "side": "BUY",
                "entry_price": 45000.0,
                "quantity": 0.001,
                "entry_time": datetime(2024, 1, 15, i, 0, 0),
                "status": "CLOSED",
            })

        trades = await repo.get_trades(filters={"limit": 2, "offset": 1})

        assert len(trades) == 2

    @pytest.mark.asyncio
    async def test_get_trade_by_id(self, repo: PostgresRepository) -> None:
        """get_trade_by_id should return the correct trade."""
        trade_id = await repo.save_trade({
            "pair": "BTCUSDT",
            "side": "BUY",
            "entry_price": 45000.0,
            "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "CLOSED",
        })

        trade = await repo.get_trade_by_id(trade_id)

        assert trade is not None
        assert trade["id"] == trade_id

    @pytest.mark.asyncio
    async def test_get_trade_by_id_not_found(
        self, repo: PostgresRepository
    ) -> None:
        """get_trade_by_id should return None for unknown ID."""
        trade = await repo.get_trade_by_id("nonexistent-id")
        assert trade is None

    @pytest.mark.asyncio
    async def test_update_trade(self, repo: PostgresRepository) -> None:
        """update_trade should modify specified fields."""
        trade_id = await repo.save_trade({
            "pair": "BTCUSDT",
            "side": "BUY",
            "entry_price": 45000.0,
            "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "OPEN",
        })

        updated = await repo.update_trade(
            trade_id, status="CLOSED", exit_price=46000.0
        )

        assert updated is not None
        assert updated["status"] == "CLOSED"
        assert updated["exit_price"] == 46000.0

    @pytest.mark.asyncio
    async def test_get_trade_stats_empty(
        self, repo: PostgresRepository
    ) -> None:
        """get_trade_stats with no trades should return zeroes."""
        stats = await repo.get_trade_stats()

        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_trade_stats_with_trades(
        self, repo: PostgresRepository
    ) -> None:
        """get_trade_stats should compute correct statistics."""
        # 2 winners + 1 loser
        await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 45000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "pnl_usdt": 10.0, "status": "CLOSED",
        })
        await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 46000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 11, 0, 0),
            "pnl_usdt": 5.0, "status": "CLOSED",
        })
        await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 47000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 12, 0, 0),
            "pnl_usdt": -3.0, "status": "CLOSED",
        })

        stats = await repo.get_trade_stats()

        assert stats["total_trades"] == 3
        assert stats["winning_trades"] == 2
        assert stats["losing_trades"] == 1
        assert abs(stats["win_rate"] - 66.666) < 1.0
        assert stats["total_pnl"] == 12.0
        assert stats["max_win"] == 10.0
        assert stats["max_loss"] == -3.0

    @pytest.mark.asyncio
    async def test_save_trade_with_metadata(
        self, repo: PostgresRepository
    ) -> None:
        """save_trade should serialize metadata to JSON."""
        trade_id = await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 45000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "CLOSED",
            "metadata": {"signal_confidence": 0.85},
        })

        trade = await repo.get_trade_by_id(trade_id)
        assert trade is not None
        assert trade["metadata_json"] is not None
        parsed = json.loads(trade["metadata_json"])
        assert parsed["signal_confidence"] == 0.85


# ======================================================================
# Tests: Strategies
# ======================================================================

class TestStrategies:
    """Test strategy CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_strategy(self, repo: PostgresRepository) -> None:
        """save_strategy should persist and return the ID."""
        strategy_id = await repo.save_strategy({
            "name": "test_strategy",
            "version": "1.0",
            "description": "A test strategy",
            "json_definition": json.dumps({
                "pairs": ["BTCUSDT"],
                "entry": {"rsi_below": 30},
            }),
            "is_active": True,
        })

        assert strategy_id is not None

    @pytest.mark.asyncio
    async def test_get_strategies(self, repo: PostgresRepository) -> None:
        """get_strategies should return all strategies."""
        await repo.save_strategy({
            "name": "strat_1",
            "json_definition": "{}",
        })
        await repo.save_strategy({
            "name": "strat_2",
            "json_definition": "{}",
        })

        strategies = await repo.get_strategies()

        assert len(strategies) == 2

    @pytest.mark.asyncio
    async def test_get_active_strategy(
        self, repo: PostgresRepository
    ) -> None:
        """get_active_strategy should return the active strategy."""
        await repo.save_strategy({
            "name": "inactive_strat",
            "json_definition": json.dumps({"pairs": ["ETHUSDT"]}),
            "is_active": False,
        })
        await repo.save_strategy({
            "name": "active_strat",
            "json_definition": json.dumps({"pairs": ["BTCUSDT"]}),
            "is_active": True,
        })

        active = await repo.get_active_strategy()

        assert active is not None
        assert active["name"] == "active_strat"

    @pytest.mark.asyncio
    async def test_get_active_strategy_none(
        self, repo: PostgresRepository
    ) -> None:
        """get_active_strategy should return None when no active strategy."""
        await repo.save_strategy({
            "name": "inactive",
            "json_definition": "{}",
            "is_active": False,
        })

        active = await repo.get_active_strategy()

        assert active is None

    @pytest.mark.asyncio
    async def test_update_strategy(self, repo: PostgresRepository) -> None:
        """update_strategy should modify the specified fields."""
        sid = await repo.save_strategy({
            "name": "updatable",
            "json_definition": "{}",
            "is_active": False,
        })

        updated = await repo.update_strategy(sid, is_active=True)

        assert updated is not None
        assert updated["is_active"] is True

    @pytest.mark.asyncio
    async def test_delete_strategy(self, repo: PostgresRepository) -> None:
        """delete_strategy should remove the strategy."""
        sid = await repo.save_strategy({
            "name": "deletable",
            "json_definition": "{}",
        })

        deleted = await repo.delete_strategy(sid)

        assert deleted is True

        # Verify it's gone
        strategies = await repo.get_strategies()
        assert len(strategies) == 0

    @pytest.mark.asyncio
    async def test_delete_strategy_not_found(
        self, repo: PostgresRepository
    ) -> None:
        """delete_strategy should return False for unknown ID."""
        deleted = await repo.delete_strategy("nonexistent-id")
        assert deleted is False


# ======================================================================
# Tests: Pairs
# ======================================================================

class TestPairs:
    """Test pair CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_pair(self, repo: PostgresRepository) -> None:
        """create_pair should persist and return the pair record."""
        pair = await repo.create_pair({
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "is_active": True,
            "min_qty": 0.00001,
            "step_size": 0.00001,
            "tick_size": 0.01,
        })

        assert pair["symbol"] == "BTCUSDT"
        assert pair["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_active_pairs(self, repo: PostgresRepository) -> None:
        """get_active_pairs should return only active pairs."""
        await repo.create_pair({
            "symbol": "BTCUSDT", "is_active": True,
        })
        await repo.create_pair({
            "symbol": "ETHUSDT", "is_active": True,
        })
        await repo.create_pair({
            "symbol": "DOGEUSDT", "is_active": False,
        })

        active = await repo.get_active_pairs()

        assert len(active) == 2
        symbols = {p["symbol"] for p in active}
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "DOGEUSDT" not in symbols

    @pytest.mark.asyncio
    async def test_update_pair(self, repo: PostgresRepository) -> None:
        """update_pair should modify the specified fields."""
        pair = await repo.create_pair({
            "symbol": "BTCUSDT", "is_active": True,
        })

        updated = await repo.update_pair(pair["id"], is_active=False)

        assert updated is not None
        assert updated["is_active"] is False


# ======================================================================
# Tests: Daily Stats
# ======================================================================

class TestDailyStats:
    """Test daily stats operations."""

    @pytest.mark.asyncio
    async def test_save_daily_stats(
        self, repo: PostgresRepository
    ) -> None:
        """save_daily_stats should persist without error."""
        await repo.save_daily_stats({
            "date": date(2024, 1, 15),
            "pair": "BTCUSDT",
            "total_trades": 5,
            "winning_trades": 3,
            "pnl_usdt": 12.5,
            "max_drawdown": 2.1,
        })
        # No error means success

    @pytest.mark.asyncio
    async def test_create_daily_stat(
        self, repo: PostgresRepository
    ) -> None:
        """create_daily_stat should return the created record."""
        stat = await repo.create_daily_stat({
            "date": date(2024, 1, 15),
            "pair": "BTCUSDT",
            "total_trades": 5,
            "winning_trades": 3,
            "pnl_usdt": 12.5,
        })

        assert stat["pair"] == "BTCUSDT"
        assert stat["total_trades"] == 5

    @pytest.mark.asyncio
    async def test_get_daily_stats_date_range(
        self, repo: PostgresRepository
    ) -> None:
        """get_daily_stats should filter by date range."""
        for i in range(5):
            await repo.create_daily_stat({
                "date": date(2024, 1, 10 + i),
                "pair": "BTCUSDT",
                "total_trades": i + 1,
            })

        stats = await repo.get_daily_stats(
            start_date=date(2024, 1, 12),
            end_date=date(2024, 1, 14),
        )

        assert len(stats) == 3


# ======================================================================
# Tests: Alerts
# ======================================================================

class TestAlerts:
    """Test alert CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_alerts(
        self, repo: PostgresRepository
    ) -> None:
        """create_alert and get_alerts should work together."""
        # Create a user first (alerts have FK to users)
        user = await repo.create_user(
            email="alert@example.com",
            hashed_password="hash",
            username="alertuser",
        )

        alert = await repo.create_alert({
            "user_id": user["id"],
            "type": "price_above",
            "condition_json": json.dumps({"price": 50000}),
            "is_active": True,
        })

        assert alert["type"] == "price_above"

        alerts = await repo.get_alerts(user["id"])
        assert len(alerts) == 1

    @pytest.mark.asyncio
    async def test_get_alerts_active_only(
        self, repo: PostgresRepository
    ) -> None:
        """get_alerts with active_only should filter inactive alerts."""
        user = await repo.create_user(
            email="active@example.com",
            hashed_password="hash",
            username="activeuser",
        )

        await repo.create_alert({
            "user_id": user["id"],
            "type": "price_above",
            "condition_json": "{}",
            "is_active": True,
        })
        await repo.create_alert({
            "user_id": user["id"],
            "type": "price_below",
            "condition_json": "{}",
            "is_active": False,
        })

        active_alerts = await repo.get_alerts(user["id"], active_only=True)
        assert len(active_alerts) == 1

    @pytest.mark.asyncio
    async def test_delete_alert(self, repo: PostgresRepository) -> None:
        """delete_alert should remove the alert."""
        user = await repo.create_user(
            email="del@example.com",
            hashed_password="hash",
            username="deluser",
        )
        alert = await repo.create_alert({
            "user_id": user["id"],
            "type": "price_above",
            "condition_json": "{}",
        })

        deleted = await repo.delete_alert(alert["id"])
        assert deleted is True

        # Verify it's gone
        alerts = await repo.get_alerts(user["id"])
        assert len(alerts) == 0


# ======================================================================
# Tests: AI Reports
# ======================================================================

class TestAIReports:
    """Test AI report CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_ai_report(
        self, repo: PostgresRepository
    ) -> None:
        """create_ai_report should return the report dict."""
        report = await repo.create_ai_report({
            "report_type": "daily",
            "content": "Market analysis for today...",
            "model_used": "gpt-4",
        })

        assert report["report_type"] == "daily"
        assert report["content"] == "Market analysis for today..."

    @pytest.mark.asyncio
    async def test_get_ai_reports_by_type(
        self, repo: PostgresRepository
    ) -> None:
        """get_ai_reports should filter by report type."""
        await repo.create_ai_report({
            "report_type": "daily",
            "content": "Daily report",
        })
        await repo.create_ai_report({
            "report_type": "weekly",
            "content": "Weekly report",
        })

        daily = await repo.get_ai_reports(report_type="daily")
        assert len(daily) == 1
        assert daily[0]["report_type"] == "daily"


# ======================================================================
# Tests: Backtests
# ======================================================================

class TestBacktests:
    """Test backtest CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_backtest(self, repo: PostgresRepository) -> None:
        """create_backtest should persist and return the record."""
        # Create a strategy first (backtests have FK)
        sid = await repo.save_strategy({
            "name": "bt_strategy",
            "json_definition": "{}",
        })

        backtest = await repo.create_backtest({
            "strategy_id": sid,
            "pair": "BTCUSDT",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
            "results_json": json.dumps({"win_rate": 65.0}),
        })

        assert backtest["pair"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_backtests_by_strategy(
        self, repo: PostgresRepository
    ) -> None:
        """get_backtests should filter by strategy ID."""
        sid = await repo.save_strategy({
            "name": "bt_filter",
            "json_definition": "{}",
        })

        await repo.create_backtest({
            "strategy_id": sid,
            "pair": "BTCUSDT",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
            "results_json": "{}",
        })

        backtests = await repo.get_backtests(strategy_id=sid)
        assert len(backtests) == 1


# ======================================================================
# Tests: Trade Journal
# ======================================================================

class TestTradeJournal:
    """Test trade journal CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_journal_entry(
        self, repo: PostgresRepository
    ) -> None:
        """create_journal_entry should persist and return the entry."""
        trade_id = await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 45000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "CLOSED",
        })

        entry = await repo.create_journal_entry({
            "trade_id": trade_id,
            "notes": "Good entry based on RSI divergence",
            "tags_json": json.dumps(["momentum", "rsi"]),
        })

        assert entry["notes"] == "Good entry based on RSI divergence"

    @pytest.mark.asyncio
    async def test_get_journal_entries(
        self, repo: PostgresRepository
    ) -> None:
        """get_journal_entries should return entries for a trade."""
        trade_id = await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 45000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "CLOSED",
        })

        await repo.create_journal_entry({
            "trade_id": trade_id,
            "notes": "Entry note",
        })
        await repo.create_journal_entry({
            "trade_id": trade_id,
            "notes": "Exit note",
        })

        entries = await repo.get_journal_entries(trade_id)
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_delete_journal_entry(
        self, repo: PostgresRepository
    ) -> None:
        """delete_journal_entry should remove the entry."""
        trade_id = await repo.save_trade({
            "pair": "BTCUSDT", "side": "BUY",
            "entry_price": 45000.0, "quantity": 0.001,
            "entry_time": datetime(2024, 1, 15, 10, 0, 0),
            "status": "CLOSED",
        })
        entry = await repo.create_journal_entry({
            "trade_id": trade_id,
            "notes": "To delete",
        })

        deleted = await repo.delete_journal_entry(entry["id"])
        assert deleted is True

        entries = await repo.get_journal_entries(trade_id)
        assert len(entries) == 0


# ======================================================================
# Tests: Notifications
# ======================================================================

class TestNotifications:
    """Test notification CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_notification(
        self, repo: PostgresRepository
    ) -> None:
        """create_notification should persist and return the record."""
        user = await repo.create_user(
            email="notif@example.com",
            hashed_password="hash",
            username="notifuser",
        )

        notif = await repo.create_notification({
            "user_id": user["id"],
            "type": "trade",
            "channel": "telegram",
            "title": "Trade executed",
            "body": "BUY BTCUSDT at 45000",
        })

        assert notif["title"] == "Trade executed"
        assert notif["is_read"] is False

    @pytest.mark.asyncio
    async def test_get_notifications_unread_only(
        self, repo: PostgresRepository
    ) -> None:
        """get_notifications with unread_only should filter read ones."""
        user = await repo.create_user(
            email="unread@example.com",
            hashed_password="hash",
            username="unreaduser",
        )

        n1 = await repo.create_notification({
            "user_id": user["id"],
            "type": "trade",
            "channel": "push",
            "title": "Unread",
        })
        n2 = await repo.create_notification({
            "user_id": user["id"],
            "type": "system",
            "channel": "push",
            "title": "Read",
        })
        await repo.mark_notification_read(n2["id"])

        unread = await repo.get_notifications(
            user["id"], unread_only=True
        )
        assert len(unread) == 1
        assert unread[0]["title"] == "Unread"

    @pytest.mark.asyncio
    async def test_mark_notification_read(
        self, repo: PostgresRepository
    ) -> None:
        """mark_notification_read should set is_read to True."""
        user = await repo.create_user(
            email="mark@example.com",
            hashed_password="hash",
            username="markuser",
        )
        notif = await repo.create_notification({
            "user_id": user["id"],
            "type": "alert",
            "channel": "email",
            "title": "Price alert",
        })

        result = await repo.mark_notification_read(notif["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_notification(
        self, repo: PostgresRepository
    ) -> None:
        """delete_notification should remove the notification."""
        user = await repo.create_user(
            email="deln@example.com",
            hashed_password="hash",
            username="delnuser",
        )
        notif = await repo.create_notification({
            "user_id": user["id"],
            "type": "trade",
            "channel": "push",
            "title": "To delete",
        })

        deleted = await repo.delete_notification(notif["id"])
        assert deleted is True

        notifs = await repo.get_notifications(user["id"])
        assert len(notifs) == 0
