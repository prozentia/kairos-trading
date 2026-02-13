"""Strategy service - business logic for strategy CRUD and validation."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.database.models import Strategy, Backtest


class StrategyService:
    """Handles strategy creation, update, validation, and activation.

    All methods are async and require an async database session.
    """

    # Required top-level keys in the strategy JSON definition
    REQUIRED_DEFINITION_KEYS = {"entry_conditions", "exit_conditions"}
    VALID_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_strategies(self, user_id: str | None = None) -> list[Strategy]:
        """Return all strategies visible to the user.

        Includes the user's own strategies AND template strategies
        (created_by IS NULL) seeded by the platform.
        """
        q = select(Strategy).order_by(Strategy.created_at.desc())
        if user_id:
            q = q.where(
                or_(Strategy.created_by == user_id, Strategy.created_by.is_(None))
            )
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Return a single strategy or None."""
        result = await self._db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def create_strategy(self, data: dict[str, Any], user_id: str | None = None) -> Strategy:
        """Create a new strategy and return it."""
        # Build the JSON definition from the structured request data
        json_definition = json.dumps({
            "name": data.get("name", ""),
            "pairs": data.get("pairs", []),
            "timeframe": data.get("timeframe", "5m"),
            "entry_conditions": [c.model_dump() if hasattr(c, "model_dump") else c
                                 for c in data.get("entry_conditions", [])],
            "exit_conditions": [c.model_dump() if hasattr(c, "model_dump") else c
                                for c in data.get("exit_conditions", [])],
            "filters": [f.model_dump() if hasattr(f, "model_dump") else f
                        for f in data.get("filters", [])],
            "risk": data["risk"].model_dump() if hasattr(data.get("risk"), "model_dump") else data.get("risk", {}),
            "indicators_needed": data.get("indicators_needed", []),
            "metadata": data.get("metadata", {}),
        })

        strategy = Strategy(
            name=data["name"],
            description=data.get("description", ""),
            json_definition=json_definition,
            created_by=user_id,
            is_active=False,
            is_validated=False,
        )
        self._db.add(strategy)
        await self._db.commit()
        await self._db.refresh(strategy)
        return strategy

    async def update_strategy(self, strategy_id: str, data: dict[str, Any]) -> Strategy | None:
        """Partial update of a strategy."""
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            return None

        # Update simple fields
        if "name" in data and data["name"] is not None:
            strategy.name = data["name"]
        if "description" in data and data["description"] is not None:
            strategy.description = data["description"]

        # Rebuild JSON definition if structured fields are provided
        current_def = json.loads(strategy.json_definition) if strategy.json_definition else {}

        update_keys = [
            "pairs", "timeframe", "entry_conditions", "exit_conditions",
            "filters", "risk", "indicators_needed", "metadata",
        ]
        changed = False
        for key in update_keys:
            if key in data and data[key] is not None:
                val = data[key]
                if isinstance(val, list):
                    current_def[key] = [
                        item.model_dump() if hasattr(item, "model_dump") else item
                        for item in val
                    ]
                elif hasattr(val, "model_dump"):
                    current_def[key] = val.model_dump()
                else:
                    current_def[key] = val
                changed = True

        if changed:
            strategy.json_definition = json.dumps(current_def)

        await self._db.commit()
        await self._db.refresh(strategy)
        return strategy

    async def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy. Returns True if deleted."""
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            return False

        await self._db.delete(strategy)
        await self._db.commit()
        return True

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    async def activate(self, strategy_id: str) -> Strategy | None:
        """Set is_active=True for a strategy."""
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            return None
        strategy.is_active = True
        await self._db.commit()
        await self._db.refresh(strategy)
        return strategy

    async def deactivate(self, strategy_id: str) -> Strategy | None:
        """Set is_active=False for a strategy."""
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            return None
        strategy.is_active = False
        await self._db.commit()
        await self._db.refresh(strategy)
        return strategy

    # ------------------------------------------------------------------
    # Duplicate
    # ------------------------------------------------------------------

    async def duplicate(self, strategy_id: str, user_id: str | None = None) -> Strategy | None:
        """Clone a strategy with a new name."""
        original = await self.get_strategy(strategy_id)
        if not original:
            return None

        clone = Strategy(
            name=f"Copy of {original.name}",
            description=original.description,
            json_definition=original.json_definition,
            created_by=user_id,
            is_active=False,
            is_validated=False,
        )
        self._db.add(clone)
        await self._db.commit()
        await self._db.refresh(clone)
        return clone

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate(self, strategy_id: str) -> dict[str, Any]:
        """Validate a strategy configuration.

        Returns {"valid": bool, "errors": [...], "warnings": [...]}.
        """
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            return {"valid": False, "errors": ["Strategy not found"], "warnings": []}

        errors: list[str] = []
        warnings: list[str] = []

        # Parse JSON definition
        try:
            definition = json.loads(strategy.json_definition)
        except (json.JSONDecodeError, TypeError):
            return {"valid": False, "errors": ["Invalid JSON definition"], "warnings": []}

        # Check required keys
        for key in self.REQUIRED_DEFINITION_KEYS:
            if key not in definition or not definition[key]:
                errors.append(f"Missing or empty required key: {key}")

        # Check timeframe
        timeframe = definition.get("timeframe", "")
        if timeframe and timeframe not in self.VALID_TIMEFRAMES:
            warnings.append(f"Unusual timeframe: {timeframe}")

        # Check entry conditions have indicator field
        for i, cond in enumerate(definition.get("entry_conditions", [])):
            if not cond.get("indicator"):
                errors.append(f"Entry condition {i + 1}: missing 'indicator' field")

        # Check exit conditions have indicator field
        for i, cond in enumerate(definition.get("exit_conditions", [])):
            if not cond.get("indicator"):
                errors.append(f"Exit condition {i + 1}: missing 'indicator' field")

        # No pairs warning
        if not definition.get("pairs"):
            warnings.append("No trading pairs specified")

        valid = len(errors) == 0

        # Update validation status in DB
        strategy.is_validated = valid
        await self._db.commit()

        return {"valid": valid, "errors": errors, "warnings": warnings}

    # ------------------------------------------------------------------
    # Backtest history
    # ------------------------------------------------------------------

    async def get_backtest_history(self, strategy_id: str) -> list[Backtest]:
        """Return all backtests for a strategy."""
        result = await self._db.execute(
            select(Backtest)
            .where(Backtest.strategy_id == strategy_id)
            .order_by(Backtest.created_at.desc())
        )
        return list(result.scalars().all())
