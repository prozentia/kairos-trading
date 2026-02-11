"""SQLAlchemy 2.0 ORM models for the Kairos Trading platform.

All tables are defined using the modern mapped_column() style with
proper relationships and indexes for performant queries.

Dependencies: sqlalchemy >= 2.0
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON user preferences")

    # Relationships
    alerts: Mapped[list[Alert]] = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_pair_entry_time", "pair", "entry_time"),
        Index("ix_trades_strategy_name", "strategy_name"),
        Index("ix_trades_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False, comment="BUY or SELL")
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    strategy_name: Mapped[str] = mapped_column(String(100), default="")
    entry_reason: Mapped[str] = mapped_column(String(500), default="")
    exit_reason: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="CLOSED", comment="OPEN, CLOSED, CANCELLED")
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON extra metadata")

    # Relationships
    journal_entries: Mapped[list[TradeJournal]] = relationship("TradeJournal", back_populates="trade", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (
        Index("ix_strategies_is_active", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    description: Mapped[str] = mapped_column(Text, default="")
    json_definition: Mapped[str] = mapped_column(Text, nullable=False, comment="Full strategy JSON definition")
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    backtest_result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON backtest summary")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    backtests: Mapped[list[Backtest]] = relationship("Backtest", back_populates="strategy", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Pair
# ---------------------------------------------------------------------------

class Pair(Base):
    __tablename__ = "pairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    exchange: Mapped[str] = mapped_column(String(20), default="binance")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    min_qty: Mapped[float] = mapped_column(Float, default=0.0)
    step_size: Mapped[float] = mapped_column(Float, default=0.0)
    tick_size: Mapped[float] = mapped_column(Float, default=0.0)


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_id", "user_id"),
        Index("ix_alerts_is_active", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, comment="price_above, price_below, pnl_target, etc.")
    condition_json: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON alert condition definition")
    channels_json: Mapped[str] = mapped_column(Text, default="[]", comment="JSON list of channels: telegram, push, email")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="alerts")


# ---------------------------------------------------------------------------
# DailyStat
# ---------------------------------------------------------------------------

class DailyStat(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (
        Index("ix_daily_stats_date_pair", "date", "pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    strategy_name: Mapped[str] = mapped_column(String(100), default="")


# ---------------------------------------------------------------------------
# AIReport
# ---------------------------------------------------------------------------

class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="daily, weekly, custom")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON metrics summary")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    strategy_id: Mapped[str] = mapped_column(String(36), ForeignKey("strategies.id"), nullable=False)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    results_json: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON backtest results")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    strategy: Mapped[Strategy] = relationship("Strategy", back_populates="backtests")


# ---------------------------------------------------------------------------
# TradeJournal
# ---------------------------------------------------------------------------

class TradeJournal(Base):
    __tablename__ = "trade_journal"
    __table_args__ = (
        Index("ix_trade_journal_trade_id", "trade_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trade_id: Mapped[str] = mapped_column(String(36), ForeignKey("trades.id"), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]", comment="JSON list of tags")
    screenshots_json: Mapped[str] = mapped_column(Text, default="[]", comment="JSON list of screenshot URLs")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    trade: Mapped[Trade] = relationship("Trade", back_populates="journal_entries")


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, comment="trade, alert, system, report")
    channel: Mapped[str] = mapped_column(String(20), nullable=False, comment="telegram, push, email, web")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="notifications")
