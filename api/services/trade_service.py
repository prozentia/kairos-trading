"""Trade service - business logic for trade operations."""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.database.models import Trade, TradeJournal


class TradeService:
    """Handles trade recording, querying, statistics, and export.

    All methods are async and require an async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_trades(
        self,
        *,
        user_id: str | None = None,
        pair: str | None = None,
        strategy: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Return paginated and filtered list of trades."""
        conditions = []
        if pair:
            conditions.append(Trade.pair == pair.upper())
        if strategy:
            conditions.append(Trade.strategy_name == strategy)
        if status:
            conditions.append(Trade.status == status.upper())
        if start_date:
            conditions.append(Trade.entry_time >= start_date)
        if end_date:
            conditions.append(Trade.entry_time <= end_date)

        where_clause = and_(*conditions) if conditions else True

        # Count total
        count_q = select(func.count(Trade.id)).where(where_clause)
        total_result = await self._db.execute(count_q)
        total = total_result.scalar() or 0

        # Fetch page
        offset = (page - 1) * per_page
        data_q = (
            select(Trade)
            .where(where_clause)
            .order_by(Trade.entry_time.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self._db.execute(data_q)
        trades = result.scalars().all()

        pages = math.ceil(total / per_page) if per_page > 0 else 0

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "trades": trades,
        }

    async def get_trade(self, trade_id: str) -> Trade | None:
        """Return a single trade or None."""
        result = await self._db.execute(select(Trade).where(Trade.id == trade_id))
        return result.scalar_one_or_none()

    async def record_trade(self, data: dict[str, Any]) -> Trade:
        """Insert a new trade record (from the engine)."""
        # Convert metadata dict to JSON string if present
        metadata = data.pop("metadata", None)
        metadata_json = json.dumps(metadata) if metadata else None

        trade = Trade(
            pair=data["pair"].upper(),
            side=data["side"].upper(),
            entry_price=data["entry_price"],
            exit_price=data.get("exit_price"),
            quantity=data["quantity"],
            entry_time=data["entry_time"],
            exit_time=data.get("exit_time"),
            pnl_usdt=data.get("pnl_usdt", 0.0),
            pnl_pct=data.get("pnl_pct", 0.0),
            fees=data.get("fees", 0.0),
            strategy_name=data.get("strategy_name", ""),
            entry_reason=data.get("entry_reason", ""),
            exit_reason=data.get("exit_reason", ""),
            status=data.get("status", "CLOSED"),
            metadata_json=metadata_json,
        )
        self._db.add(trade)
        await self._db.commit()
        await self._db.refresh(trade)
        return trade

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def compute_stats(
        self,
        *,
        user_id: str | None = None,
        pair: str | None = None,
        strategy: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Compute aggregated statistics over trades."""
        conditions = [Trade.status == "CLOSED"]
        if pair:
            conditions.append(Trade.pair == pair.upper())
        if strategy:
            conditions.append(Trade.strategy_name == strategy)
        if start_date:
            conditions.append(Trade.entry_time >= start_date)
        if end_date:
            conditions.append(Trade.entry_time <= end_date)

        where_clause = and_(*conditions)

        result = await self._db.execute(select(Trade).where(where_clause))
        trades = result.scalars().all()

        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl_usdt": 0.0,
                "total_pnl_pct": 0.0,
                "average_pnl_usdt": 0.0,
                "max_win_usdt": 0.0,
                "max_loss_usdt": 0.0,
                "average_duration_minutes": 0.0,
                "profit_factor": 0.0,
            }

        total_trades = len(trades)
        winning = [t for t in trades if t.pnl_usdt > 0]
        losing = [t for t in trades if t.pnl_usdt < 0]
        total_pnl = sum(t.pnl_usdt for t in trades)
        total_pnl_pct = sum(t.pnl_pct for t in trades)
        pnls = [t.pnl_usdt for t in trades]

        # Average duration in minutes
        durations = []
        for t in trades:
            if t.entry_time and t.exit_time:
                delta = (t.exit_time - t.entry_time).total_seconds() / 60.0
                durations.append(delta)
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Profit factor = gross_profit / gross_loss
        gross_profit = sum(t.pnl_usdt for t in winning) if winning else 0.0
        gross_loss = abs(sum(t.pnl_usdt for t in losing)) if losing else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / total_trades * 100, 2) if total_trades else 0.0,
            "total_pnl_usdt": round(total_pnl, 4),
            "total_pnl_pct": round(total_pnl_pct, 4),
            "average_pnl_usdt": round(total_pnl / total_trades, 4) if total_trades else 0.0,
            "max_win_usdt": round(max(pnls), 4) if pnls else 0.0,
            "max_loss_usdt": round(min(pnls), 4) if pnls else 0.0,
            "average_duration_minutes": round(avg_duration, 2),
            "profit_factor": round(profit_factor, 4),
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_csv(
        self,
        *,
        user_id: str | None = None,
        pair: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Generate CSV content for trade export."""
        conditions = []
        if pair:
            conditions.append(Trade.pair == pair.upper())
        if start_date:
            conditions.append(Trade.entry_time >= start_date)
        if end_date:
            conditions.append(Trade.entry_time <= end_date)

        where_clause = and_(*conditions) if conditions else True

        result = await self._db.execute(
            select(Trade).where(where_clause).order_by(Trade.entry_time.desc())
        )
        trades = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "pair", "side", "entry_price", "exit_price",
            "quantity", "entry_time", "exit_time", "pnl_usdt",
            "pnl_pct", "fees", "strategy_name", "entry_reason",
            "exit_reason", "status",
        ])

        for t in trades:
            writer.writerow([
                t.id, t.pair, t.side, t.entry_price, t.exit_price,
                t.quantity, t.entry_time, t.exit_time, t.pnl_usdt,
                t.pnl_pct, t.fees, t.strategy_name, t.entry_reason,
                t.exit_reason, t.status,
            ])

        return output.getvalue()

    # ------------------------------------------------------------------
    # Journal
    # ------------------------------------------------------------------

    async def add_journal_entry(
        self,
        trade_id: str,
        notes: str,
        tags: list[str] | None = None,
        rating: int | None = None,
    ) -> TradeJournal:
        """Add a journal entry to a trade."""
        # Verify trade exists
        trade = await self.get_trade(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")

        entry = TradeJournal(
            trade_id=trade_id,
            notes=notes,
            tags_json=json.dumps(tags or []),
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def get_journal_entries(self, trade_id: str) -> list[TradeJournal]:
        """Get all journal entries for a trade."""
        result = await self._db.execute(
            select(TradeJournal)
            .where(TradeJournal.trade_id == trade_id)
            .order_by(TradeJournal.created_at.desc())
        )
        return list(result.scalars().all())
