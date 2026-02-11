"""Common schemas shared across the API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(50, ge=1, le=200, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses."""

    total: int
    page: int
    per_page: int
    pages: int


# ---------------------------------------------------------------------------
# Date range
# ---------------------------------------------------------------------------

class DateRangeParams(BaseModel):
    """Query parameters for date-range filtering."""

    model_config = ConfigDict(frozen=True)

    start_date: datetime | None = Field(None, description="Inclusive start")
    end_date: datetime | None = Field(None, description="Inclusive end")


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    """Standard success envelope."""

    success: bool = True
    message: str = "OK"
    data: dict | list | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    error: str
    detail: str | None = None
