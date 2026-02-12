"""Alerts router - CRUD and triggered alert history."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user
from api.deps import get_db
from api.schemas.common import SuccessResponse
from adapters.database.models import Alert

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

    id: str
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

    id: str
    alert_id: str
    triggered_at: str
    message_sent: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alert_to_response(alert: Alert) -> AlertResponse:
    """Convert an Alert ORM object to response dict."""
    try:
        condition = json.loads(alert.condition_json)
    except (json.JSONDecodeError, TypeError):
        condition = {}

    try:
        channels = json.loads(alert.channels_json)
    except (json.JSONDecodeError, TypeError):
        channels = []

    # Extract pair from condition if not stored separately
    # The Alert model doesn't have a direct 'pair' column, but condition_json
    # holds it. We store the pair in condition_json for simplicity.
    pair = condition.get("pair", "")

    return AlertResponse(
        id=alert.id,
        pair=pair,
        type=alert.type,
        condition=condition,
        message=condition.get("message", ""),
        channels=channels,
        enabled=alert.is_active,
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        triggered_count=1 if alert.triggered_at else 0,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all configured alerts."""
    user_id = current_user.get("sub")
    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == user_id)
        .order_by(Alert.created_at.desc())
    )
    alerts = result.scalars().all()
    return [_alert_to_response(a) for a in alerts]


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreateRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert."""
    user_id = current_user.get("sub")

    # Build condition JSON with pair and message included
    condition = body.condition.copy()
    condition["pair"] = body.pair.upper()
    condition["message"] = body.message

    alert = Alert(
        user_id=user_id,
        type=body.type,
        condition_json=json.dumps(condition),
        channels_json=json.dumps(body.channels),
        is_active=body.enabled,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return _alert_to_response(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    body: AlertUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing alert."""
    user_id = current_user.get("sub")
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    # Update fields
    if body.type is not None:
        alert.type = body.type

    if body.enabled is not None:
        alert.is_active = body.enabled

    if body.channels is not None:
        alert.channels_json = json.dumps(body.channels)

    # Update condition JSON
    if body.condition is not None or body.pair is not None or body.message is not None:
        try:
            current_condition = json.loads(alert.condition_json)
        except (json.JSONDecodeError, TypeError):
            current_condition = {}

        if body.condition is not None:
            current_condition.update(body.condition)
        if body.pair is not None:
            current_condition["pair"] = body.pair.upper()
        if body.message is not None:
            current_condition["message"] = body.message

        alert.condition_json = json.dumps(current_condition)

    await db.commit()
    await db.refresh(alert)

    return _alert_to_response(alert)


@router.delete("/{alert_id}", response_model=SuccessResponse)
async def delete_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert."""
    user_id = current_user.get("sub")
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    await db.delete(alert)
    await db.commit()
    return SuccessResponse(message=f"Alert {alert_id} deleted")


# ---------------------------------------------------------------------------
# Triggered history
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[AlertHistoryEntry])
async def alert_history(
    alert_id: str | None = Query(None, description="Filter by alert ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get history of triggered alerts."""
    user_id = current_user.get("sub")
    q = select(Alert).where(
        Alert.user_id == user_id,
        Alert.triggered_at.isnot(None),
    ).order_by(Alert.triggered_at.desc()).limit(limit)

    if alert_id:
        q = q.where(Alert.id == alert_id)

    result = await db.execute(q)
    alerts = result.scalars().all()

    return [
        AlertHistoryEntry(
            id=a.id,
            alert_id=a.id,
            triggered_at=a.triggered_at.isoformat() if a.triggered_at else "",
            message_sent=json.loads(a.condition_json).get("message", "")
            if a.condition_json else "",
        )
        for a in alerts
    ]
