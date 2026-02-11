"""Strategy service - business logic for strategy CRUD and validation."""

from __future__ import annotations

from typing import Any


class StrategyService:
    """Handles strategy creation, update, validation, and activation.

    All methods are async-ready for use with an async database session.
    """

    def __init__(self, db_session: Any = None) -> None:
        self._db = db_session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_strategies(self) -> list[dict]:
        """Return all strategies."""
        # TODO: query from DB
        return []

    async def get_strategy(self, strategy_id: int) -> dict | None:
        """Return a single strategy or None."""
        # TODO: query by ID
        return None

    async def create_strategy(self, data: dict) -> dict:
        """Create a new strategy and return it."""
        # TODO: validate + insert
        return data

    async def update_strategy(self, strategy_id: int, data: dict) -> dict | None:
        """Partial update of a strategy."""
        # TODO: update in DB
        return None

    async def delete_strategy(self, strategy_id: int) -> bool:
        """Delete a strategy. Returns True if deleted."""
        # TODO: delete from DB
        return False

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    async def activate(self, strategy_id: int) -> bool:
        """Set is_active=True for a strategy."""
        # TODO: update in DB
        return True

    async def deactivate(self, strategy_id: int) -> bool:
        """Set is_active=False for a strategy."""
        # TODO: update in DB
        return True

    # ------------------------------------------------------------------
    # Duplicate
    # ------------------------------------------------------------------

    async def duplicate(self, strategy_id: int) -> dict | None:
        """Clone a strategy with a new name."""
        # TODO: read original, copy with name = "Copy of <name>"
        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate(self, strategy_id: int) -> dict:
        """Validate a strategy configuration.

        Returns {"valid": bool, "errors": [...], "warnings": [...]}.
        """
        # TODO: check indicators exist, conditions are valid, etc.
        return {"valid": True, "errors": [], "warnings": []}

    # ------------------------------------------------------------------
    # Backtest history
    # ------------------------------------------------------------------

    async def get_backtest_history(self, strategy_id: int) -> list[dict]:
        """Return all backtests for a strategy."""
        # TODO: query backtests table filtered by strategy_id
        return []
