"""AI Reports router - generate, retrieve, manage AI analysis reports."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth.jwt import get_current_active_user
from api.schemas.common import SuccessResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class AIReportResponse(BaseModel):
    """AI-generated trading report."""

    id: int
    title: str
    content: str
    model_used: str
    total_trades_analysed: int = 0
    win_rate: float | None = None
    total_pnl_usdt: float | None = None
    recommendations: list[str] = Field(default_factory=list)
    status: str = "completed"  # pending, generating, completed, failed
    progress_pct: float = 100.0
    created_at: str
    generation_time_seconds: float = 0.0


class AIReportStatusResponse(BaseModel):
    """Progress of a report being generated."""

    id: int
    status: str = "pending"
    progress_pct: float = 0.0
    message: str = ""


class PromptResponse(BaseModel):
    """System prompt for report generation."""

    prompt: str


class PromptUpdateRequest(BaseModel):
    """Body for PUT /ai-reports/prompt."""

    prompt: str = Field(..., min_length=10, max_length=10000)


# ---------------------------------------------------------------------------
# Latest / History
# ---------------------------------------------------------------------------

@router.get("/latest", response_model=AIReportResponse | None)
async def get_latest_report(
    current_user: dict = Depends(get_current_active_user),
):
    """Get the most recent AI report."""
    # TODO: query latest from DB
    return None


@router.get("/history", response_model=list[AIReportResponse])
async def report_history(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user),
):
    """Get list of previous AI reports."""
    # TODO: query from DB
    return []


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=AIReportStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    current_user: dict = Depends(get_current_active_user),
):
    """Launch AI report generation (async task).

    Collects recent trade data, sends to OpenRouter LLM, and stores
    the analysis. Use GET /ai-reports/{id}/status to poll progress.
    """
    # TODO: enqueue report generation task
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Report generation not yet implemented",
    )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/{report_id}/status", response_model=AIReportStatusResponse)
async def report_status(
    report_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get progress of a report being generated."""
    # TODO: check task status
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Report {report_id} not found",
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{report_id}", response_model=SuccessResponse)
async def delete_report(
    report_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete an AI report."""
    # TODO: delete from DB
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Report {report_id} not found",
    )


# ---------------------------------------------------------------------------
# Prompt management
# ---------------------------------------------------------------------------

@router.get("/prompt", response_model=PromptResponse)
async def get_prompt(
    current_user: dict = Depends(get_current_active_user),
):
    """Get the current system prompt used for report generation."""
    # TODO: read from config file / DB
    return PromptResponse(
        prompt="You are an expert trading analyst. Analyse the following trades..."
    )


@router.put("/prompt", response_model=SuccessResponse)
async def update_prompt(
    body: PromptUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update the system prompt used for report generation."""
    # TODO: write to config file / DB
    return SuccessResponse(message="Prompt updated")
