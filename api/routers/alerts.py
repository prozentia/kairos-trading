"""Alerts router - CRUD and triggered alert history."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class AlertCreateRequest(BaseModel):
    """Body for POST /alerts/."""

    pair: str
    type: str = Field(..., description="price_above, price_below, pnl_threshold, indicator")
    condition: dict = Field(default_factory=dict, description="Condition parameters")
    message: str = ""
    channels: list[str] = Field(default_factory=lambda: ["telegram"])
    enabled: bool = True


class AlertUpdateRequest(BaseModel):
    """Body for PUT /alerts/{id}."""

    pair: str | None = None
    type: str | None = None
    condition: dict | None = None
    message: str | None = None
    channels: list[str] | None = None
    enabled: bool | None = None


class AlertResponse(BaseModel):
    """Alert representation."""

    id: int
    pair: str
    type: str
    condition: dict
    message: str
    channels: list[str]
    enabled: bool
    created_at: str
    triggered_count: int = 0


class AlertHistoryEntry(BaseModel):
    """A single triggered alert event."""

    id: int
    alert_id: int
    triggered_at: str
    price_at_trigger: float
    message_sent: str


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    current_user: dict = Depends(get_current_active_user),
):
    """List all configured alerts."""
    # TODO: query from DB
    return []


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new alert."""
    # TODO: insert into DB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert creation not yet wired to the database",
    )


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    body: AlertUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update an existing alert."""
    # TODO: update in DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert {alert_id} not found",
    )


@router.delete("/{alert_id}", response_model=SuccessResponse)
async def delete_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete an alert."""
    # TODO: delete from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert {alert_id} not found",
    )


# ---------------------------------------------------------------------------
# Triggered history
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[AlertHistoryEntry])
async def alert_history(
    alert_id: int | None = Query(None, description="Filter by alert ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_active_user),
):
    """Get history of triggered alerts."""
    # TODO: query from DB
    return []
