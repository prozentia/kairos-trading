"""AI Reports router - generate, retrieve, manage AI analysis reports."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt import get_current_active_user
from api.deps import get_db
from api.schemas.common import SuccessResponse
from api.services.report_generator import ReportGenerator

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas (local to this router)
# ---------------------------------------------------------------------------

class AIReportResponse(BaseModel):
    """AI-generated trading report."""

    id: str
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

    id: str
    status: str = "pending"
    progress_pct: float = 0.0
    message: str = ""


class PromptResponse(BaseModel):
    """System prompt for report generation."""

    prompt: str


class PromptUpdateRequest(BaseModel):
    """Body for PUT /ai-reports/prompt."""

    prompt: str = Field(..., min_length=10, max_length=10000)


# In-memory prompt storage (can be upgraded to DB)
_report_generator_prompt: str | None = None


# ---------------------------------------------------------------------------
# Latest / History
# ---------------------------------------------------------------------------

@router.get("/latest", response_model=AIReportResponse | None)
async def get_latest_report(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent AI report."""
    generator = ReportGenerator(db=db)
    report = await generator.get_latest()
    if not report:
        return None
    return AIReportResponse(**report)


@router.get("/history", response_model=list[AIReportResponse])
async def report_history(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of previous AI reports."""
    generator = ReportGenerator(db=db)
    reports = await generator.get_reports(limit=limit)
    return [AIReportResponse(**r) for r in reports]


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=AIReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Launch AI report generation.

    Collects recent trade data, sends to OpenRouter LLM, and stores
    the analysis.
    """
    global _report_generator_prompt
    generator = ReportGenerator(db=db)
    if _report_generator_prompt:
        generator.set_prompt(_report_generator_prompt)

    report = await generator.generate(user_id=current_user.get("sub"))
    return AIReportResponse(**report)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/{report_id}/status", response_model=AIReportStatusResponse)
async def report_status(
    report_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get progress of a report being generated."""
    generator = ReportGenerator(db=db)
    report = await generator.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )
    return AIReportStatusResponse(
        id=report["id"],
        status=report.get("status", "completed"),
        progress_pct=report.get("progress_pct", 100.0),
        message="",
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{report_id}", response_model=SuccessResponse)
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an AI report."""
    generator = ReportGenerator(db=db)
    deleted = await generator.delete_report(report_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )
    return SuccessResponse(message=f"Report {report_id} deleted")


# ---------------------------------------------------------------------------
# Prompt management
# ---------------------------------------------------------------------------

@router.get("/prompt", response_model=PromptResponse)
async def get_prompt(
    current_user: dict = Depends(get_current_active_user),
):
    """Get the current system prompt used for report generation."""
    global _report_generator_prompt
    generator = ReportGenerator()
    if _report_generator_prompt:
        generator.set_prompt(_report_generator_prompt)
    return PromptResponse(prompt=generator.get_prompt())


@router.put("/prompt", response_model=SuccessResponse)
async def update_prompt(
    body: PromptUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Update the system prompt used for report generation."""
    global _report_generator_prompt
    _report_generator_prompt = body.prompt
    return SuccessResponse(message="Prompt updated")
