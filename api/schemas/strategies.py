"""Strategy-related schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class ConditionSchema(BaseModel):
    """A single entry/exit condition block."""

    indicator: str = Field(..., description="Indicator name (e.g. 'rsi', 'ema_cross')")
    params: dict[str, Any] = Field(default_factory=dict)
    operator: str = Field("", description="Comparison operator (lt, gt, eq, cross_above, etc.)")
    value: float | str | None = None


class FilterSchema(BaseModel):
    """A post-signal filter (volume, time, cooldown, etc.)."""

    type: str = Field(..., description="Filter type")
    params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class RiskConfigSchema(BaseModel):
    """Risk parameters for a strategy."""

    stop_loss_pct: float = 1.5
    trailing_activation_pct: float = 0.6
    trailing_distance_pct: float = 0.3
    take_profit_levels: list[dict[str, float]] = Field(default_factory=list)
    max_position_size_pct: float = 10.0


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class StrategyCreateRequest(BaseModel):
    """Body for POST /strategies/."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    pairs: list[str] = Field(default_factory=list)
    timeframe: str = "5m"
    entry_conditions: list[ConditionSchema] = Field(default_factory=list)
    exit_conditions: list[ConditionSchema] = Field(default_factory=list)
    filters: list[FilterSchema] = Field(default_factory=list)
    risk: RiskConfigSchema = Field(default_factory=RiskConfigSchema)
    indicators_needed: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyUpdateRequest(BaseModel):
    """Body for PUT /strategies/{id} (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    pairs: list[str] | None = None
    timeframe: str | None = None
    entry_conditions: list[ConditionSchema] | None = None
    exit_conditions: list[ConditionSchema] | None = None
    filters: list[FilterSchema] | None = None
    risk: RiskConfigSchema | None = None
    indicators_needed: list[str] | None = None
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class StrategyResponse(BaseModel):
    """Full strategy representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    version: str = "1.0"
    pairs: list[str]
    timeframe: str
    entry_conditions: list[dict[str, Any]]
    exit_conditions: list[dict[str, Any]]
    filters: list[dict[str, Any]]
    risk: dict[str, Any]
    indicators_needed: list[str]
    is_active: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None = None


class StrategyListResponse(BaseModel):
    """List of strategies."""

    total: int
    strategies: list[StrategyResponse]


class StrategyValidationResponse(BaseModel):
    """Result of strategy validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
