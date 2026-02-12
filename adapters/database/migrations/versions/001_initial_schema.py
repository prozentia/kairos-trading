"""Initial schema - 10 tables.

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-12

Creates all 10 tables for the Kairos Trading platform:
- users
- trades
- strategies
- pairs
- alerts
- daily_stats
- ai_reports
- backtests
- trade_journal
- notifications
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- users ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("preferences", sa.Text(), nullable=True, comment="JSON user preferences"),
    )

    # -- trades --------------------------------------------------------------
    op.create_table(
        "trades",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pair", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False, comment="BUY or SELL"),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("entry_time", sa.DateTime(), nullable=False),
        sa.Column("exit_time", sa.DateTime(), nullable=True),
        sa.Column("pnl_usdt", sa.Float(), default=0.0),
        sa.Column("pnl_pct", sa.Float(), default=0.0),
        sa.Column("fees", sa.Float(), default=0.0),
        sa.Column("strategy_name", sa.String(100), default=""),
        sa.Column("entry_reason", sa.String(500), default=""),
        sa.Column("exit_reason", sa.String(500), default=""),
        sa.Column("status", sa.String(20), default="CLOSED", comment="OPEN, CLOSED, CANCELLED"),
        sa.Column("metadata_json", sa.Text(), nullable=True, comment="JSON extra metadata"),
    )
    op.create_index("ix_trades_pair_entry_time", "trades", ["pair", "entry_time"])
    op.create_index("ix_trades_strategy_name", "trades", ["strategy_name"])
    op.create_index("ix_trades_status", "trades", ["status"])

    # -- strategies ----------------------------------------------------------
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("version", sa.String(20), default="1.0"),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("json_definition", sa.Text(), nullable=False, comment="Full strategy JSON definition"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=False),
        sa.Column("is_validated", sa.Boolean(), default=False),
        sa.Column("total_trades", sa.Integer(), default=0),
        sa.Column("winning_trades", sa.Integer(), default=0),
        sa.Column("total_pnl", sa.Float(), default=0.0),
        sa.Column("backtest_result", sa.Text(), nullable=True, comment="JSON backtest summary"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_strategies_is_active", "strategies", ["is_active"])

    # -- pairs ---------------------------------------------------------------
    op.create_table(
        "pairs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("exchange", sa.String(20), default="binance"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("min_qty", sa.Float(), default=0.0),
        sa.Column("step_size", sa.Float(), default=0.0),
        sa.Column("tick_size", sa.Float(), default=0.0),
    )

    # -- alerts --------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, comment="price_above, price_below, pnl_target, etc."),
        sa.Column("condition_json", sa.Text(), nullable=False, comment="JSON alert condition definition"),
        sa.Column("channels_json", sa.Text(), default="[]", comment="JSON list of channels"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_is_active", "alerts", ["is_active"])

    # -- daily_stats ---------------------------------------------------------
    op.create_table(
        "daily_stats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("pair", sa.String(20), nullable=False),
        sa.Column("total_trades", sa.Integer(), default=0),
        sa.Column("winning_trades", sa.Integer(), default=0),
        sa.Column("pnl_usdt", sa.Float(), default=0.0),
        sa.Column("max_drawdown", sa.Float(), default=0.0),
        sa.Column("strategy_name", sa.String(100), default=""),
    )
    op.create_index("ix_daily_stats_date_pair", "daily_stats", ["date", "pair"])

    # -- ai_reports ----------------------------------------------------------
    op.create_table(
        "ai_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_type", sa.String(50), nullable=False, comment="daily, weekly, custom"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=True, comment="JSON metrics summary"),
        sa.Column("model_used", sa.String(100), default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), index=True),
    )

    # -- backtests -----------------------------------------------------------
    op.create_table(
        "backtests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("strategy_id", sa.String(36), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("pair", sa.String(20), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("results_json", sa.Text(), nullable=False, comment="JSON backtest results"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # -- trade_journal -------------------------------------------------------
    op.create_table(
        "trade_journal",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trade_id", sa.String(36), sa.ForeignKey("trades.id"), nullable=False),
        sa.Column("notes", sa.Text(), default=""),
        sa.Column("tags_json", sa.Text(), default="[]", comment="JSON list of tags"),
        sa.Column("screenshots_json", sa.Text(), default="[]", comment="JSON list of screenshot URLs"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_trade_journal_trade_id", "trade_journal", ["trade_id"])

    # -- notifications -------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, comment="trade, alert, system, report"),
        sa.Column("channel", sa.String(20), nullable=False, comment="telegram, push, email, web"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), default=""),
        sa.Column("is_read", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), index=True),
    )
    op.create_index("ix_notifications_user_id_is_read", "notifications", ["user_id", "is_read"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("trade_journal")
    op.drop_table("backtests")
    op.drop_table("ai_reports")
    op.drop_table("daily_stats")
    op.drop_table("alerts")
    op.drop_table("pairs")
    op.drop_table("strategies")
    op.drop_table("trades")
    op.drop_table("users")
