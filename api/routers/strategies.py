"""Strategies router - CRUD, activate/deactivate, duplicate, validate."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user
from api.deps import get_db
from api.schemas.common import SuccessResponse
from api.schemas.strategies import (
    StrategyCreateRequest,
    StrategyListResponse,
    StrategyResponse,
    StrategyUpdateRequest,
    StrategyValidationResponse,
)
from api.services.strategy_service import StrategyService

router = APIRouter()


# ---------------------------------------------------------------------------
# List / Read
# ---------------------------------------------------------------------------

@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all strategies."""
    service = StrategyService(db)
    strategies = await service.list_strategies(user_id=current_user.get("sub"))
    return StrategyListResponse(
        total=len(strategies),
        strategies=[StrategyResponse.model_validate(s) for s in strategies],
    )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single strategy by ID."""
    service = StrategyService(db)
    strategy = await service.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return StrategyResponse.model_validate(strategy)


# ---------------------------------------------------------------------------
# Create / Update / Delete
# ---------------------------------------------------------------------------

@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    body: StrategyCreateRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new strategy."""
    service = StrategyService(db)
    strategy = await service.create_strategy(
        data=body.model_dump(),
        user_id=current_user.get("sub"),
    )
    return StrategyResponse.model_validate(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    body: StrategyUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing strategy."""
    service = StrategyService(db)
    strategy = await service.update_strategy(strategy_id, body.model_dump(exclude_unset=True))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return StrategyResponse.model_validate(strategy)


@router.delete("/{strategy_id}", response_model=SuccessResponse)
async def delete_strategy(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategy."""
    service = StrategyService(db)
    deleted = await service.delete_strategy(strategy_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return SuccessResponse(message=f"Strategy {strategy_id} deleted")


# ---------------------------------------------------------------------------
# Activate / Deactivate
# ---------------------------------------------------------------------------

@router.post("/{strategy_id}/activate", response_model=SuccessResponse)
async def activate_strategy(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate a strategy for live trading."""
    service = StrategyService(db)
    strategy = await service.activate(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return SuccessResponse(message=f"Strategy {strategy_id} activated")


@router.post("/{strategy_id}/deactivate", response_model=SuccessResponse)
async def deactivate_strategy(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a strategy."""
    service = StrategyService(db)
    strategy = await service.deactivate(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return SuccessResponse(message=f"Strategy {strategy_id} deactivated")


# ---------------------------------------------------------------------------
# Duplicate
# ---------------------------------------------------------------------------

@router.post("/{strategy_id}/duplicate", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_strategy(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a copy of an existing strategy."""
    service = StrategyService(db)
    clone = await service.duplicate(strategy_id, user_id=current_user.get("sub"))
    if not clone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    return StrategyResponse.model_validate(clone)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@router.post("/{strategy_id}/validate", response_model=StrategyValidationResponse)
async def validate_strategy(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a strategy configuration."""
    service = StrategyService(db)
    result = await service.validate(strategy_id)
    return StrategyValidationResponse(**result)


# ---------------------------------------------------------------------------
# Backtest history
# ---------------------------------------------------------------------------

@router.get("/{strategy_id}/backtest-history")
async def strategy_backtest_history(
    strategy_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get backtest history for a specific strategy."""
    service = StrategyService(db)
    history = await service.get_backtest_history(strategy_id)
    return history
