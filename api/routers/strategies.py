"""Strategies router - CRUD, activate/deactivate, duplicate, validate."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse
from api.schemas.strategies import (
    StrategyCreateRequest,
    StrategyListResponse,
    StrategyResponse,
    StrategyUpdateRequest,
    StrategyValidationResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# List / Read
# ---------------------------------------------------------------------------

@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    current_user: dict = Depends(get_current_active_user),
):
    """List all strategies."""
    # TODO: query strategies from DB
    return StrategyListResponse(total=0, strategies=[])


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get a single strategy by ID."""
    # TODO: query from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Strategy {strategy_id} not found",
    )


# ---------------------------------------------------------------------------
# Create / Update / Delete
# ---------------------------------------------------------------------------

@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    body: StrategyCreateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new strategy."""
    # TODO: validate and insert into DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Strategy creation not yet wired to the database",
    )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    body: StrategyUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update an existing strategy."""
    # TODO: update in DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Strategy {strategy_id} not found",
    )


@router.delete("/{strategy_id}", response_model=SuccessResponse)
async def delete_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a strategy."""
    # TODO: soft-delete or hard-delete from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Strategy {strategy_id} not found",
    )


# ---------------------------------------------------------------------------
# Activate / Deactivate
# ---------------------------------------------------------------------------

@router.post("/{strategy_id}/activate", response_model=SuccessResponse)
async def activate_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Activate a strategy for live trading."""
    # TODO: set is_active=True in DB
    return SuccessResponse(message=f"Strategy {strategy_id} activated")


@router.post("/{strategy_id}/deactivate", response_model=SuccessResponse)
async def deactivate_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Deactivate a strategy."""
    # TODO: set is_active=False in DB
    return SuccessResponse(message=f"Strategy {strategy_id} deactivated")


# ---------------------------------------------------------------------------
# Duplicate
# ---------------------------------------------------------------------------

@router.post("/{strategy_id}/duplicate", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Create a copy of an existing strategy."""
    # TODO: read strategy, clone with new name, insert
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Strategy {strategy_id} not found",
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@router.post("/{strategy_id}/validate", response_model=StrategyValidationResponse)
async def validate_strategy(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Validate a strategy configuration."""
    # TODO: run validation logic from strategy_service
    return StrategyValidationResponse(valid=True)


# ---------------------------------------------------------------------------
# Backtest history
# ---------------------------------------------------------------------------

@router.get("/{strategy_id}/backtest-history")
async def strategy_backtest_history(
    strategy_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get backtest history for a specific strategy."""
    # TODO: query backtests for this strategy
    return []
