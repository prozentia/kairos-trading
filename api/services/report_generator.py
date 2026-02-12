"""AI report generator service - generates trading analysis via OpenRouter.

Collects recent trade data, formats it as a prompt, sends it to an
LLM via OpenRouter, and parses the structured response.  Reports are
persisted in the ai_reports table.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.database.models import AIReport, Trade


class ReportGenerator:
    """Generates AI-powered trading analysis reports."""

    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        db: AsyncSession | None = None,
        api_key: str | None = None,
        model: str = "anthropic/claude-sonnet-4",
    ) -> None:
        self._db = db
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self._model = model
        self._default_prompt = (
            "You are an expert crypto trading analyst. "
            "Analyse the following trades and provide actionable insights, "
            "a performance summary, and recommendations for improvement. "
            "Structure your response with the sections: "
            "## Performance Summary, ## Key Observations, ## Recommendations."
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        trades: list[dict[str, Any]] | None = None,
        custom_prompt: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a full analysis report from trade data.

        If no trades are provided, fetches the last 50 closed trades from DB.
        Returns a dict with: id, title, content, recommendations, model_used,
        total_trades_analysed, status, created_at.
        """
        start_time = time.monotonic()
        prompt = custom_prompt or self._default_prompt

        # Fetch trades from DB if not provided
        if trades is None and self._db:
            result = await self._db.execute(
                select(Trade)
                .where(Trade.status == "CLOSED")
                .order_by(Trade.entry_time.desc())
                .limit(50)
            )
            db_trades = result.scalars().all()
            trades = [
                {
                    "pair": t.pair,
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "pnl_usdt": t.pnl_usdt,
                    "pnl_pct": t.pnl_pct,
                    "entry_reason": t.entry_reason,
                    "exit_reason": t.exit_reason,
                    "strategy_name": t.strategy_name,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else "",
                    "exit_time": t.exit_time.isoformat() if t.exit_time else "",
                }
                for t in db_trades
            ]

        trades = trades or []

        # Format trades for the LLM
        trade_summary = self._format_trades(trades)

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Here are my recent trades ({len(trades)} total):\n\n"
                    f"{trade_summary}\n\nPlease analyse."
                ),
            },
        ]

        # Call OpenRouter
        content = await self._call_openrouter(messages)
        generation_time = time.monotonic() - start_time

        # Compute basic stats from trades
        total_pnl = sum(t.get("pnl_usdt", 0) for t in trades)
        winning = sum(1 for t in trades if t.get("pnl_usdt", 0) > 0)
        win_rate = (winning / len(trades) * 100) if trades else 0.0

        # Parse recommendations from content
        recommendations = self._extract_recommendations(content)

        # Build report data
        report_data = {
            "title": f"Trading Analysis - {len(trades)} trades",
            "content": content,
            "model_used": self._model,
            "total_trades_analysed": len(trades),
            "win_rate": round(win_rate, 2),
            "total_pnl_usdt": round(total_pnl, 4),
            "recommendations": recommendations,
            "status": "completed",
            "generation_time_seconds": round(generation_time, 2),
        }

        # Persist to DB
        if self._db:
            metrics = json.dumps({
                "total_trades": len(trades),
                "win_rate": report_data["win_rate"],
                "total_pnl_usdt": report_data["total_pnl_usdt"],
                "recommendations": recommendations,
                "generation_time_seconds": report_data["generation_time_seconds"],
            })

            ai_report = AIReport(
                report_type="daily",
                content=content,
                metrics_json=metrics,
                model_used=self._model,
            )
            self._db.add(ai_report)
            await self._db.commit()
            await self._db.refresh(ai_report)
            report_data["id"] = ai_report.id
            report_data["created_at"] = ai_report.created_at.isoformat()

        return report_data

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def get_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the latest AI reports from DB."""
        if not self._db:
            return []

        result = await self._db.execute(
            select(AIReport)
            .order_by(AIReport.created_at.desc())
            .limit(limit)
        )
        reports = result.scalars().all()

        return [self._report_to_dict(r) for r in reports]

    async def get_latest(self) -> dict[str, Any] | None:
        """Get the most recent AI report."""
        if not self._db:
            return None

        result = await self._db.execute(
            select(AIReport)
            .order_by(AIReport.created_at.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()
        if not report:
            return None

        return self._report_to_dict(report)

    async def get_report(self, report_id: str) -> dict[str, Any] | None:
        """Get a specific report by ID."""
        if not self._db:
            return None

        result = await self._db.execute(
            select(AIReport).where(AIReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return None

        return self._report_to_dict(report)

    async def delete_report(self, report_id: str) -> bool:
        """Delete a report. Returns True if deleted."""
        if not self._db:
            return False

        result = await self._db.execute(
            select(AIReport).where(AIReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return False

        await self._db.delete(report)
        await self._db.commit()
        return True

    # ------------------------------------------------------------------
    # Prompt management
    # ------------------------------------------------------------------

    def get_prompt(self) -> str:
        """Return the current system prompt."""
        return self._default_prompt

    def set_prompt(self, prompt: str) -> None:
        """Update the system prompt (in-memory; persist externally)."""
        self._default_prompt = prompt

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_trades(self, trades: list[dict[str, Any]]) -> str:
        """Format trade data as a readable text block for the LLM."""
        if not trades:
            return "No trades to analyse."

        lines: list[str] = []
        for i, t in enumerate(trades, 1):
            lines.append(
                f"{i}. {t.get('pair', '?')} | {t.get('side', '?')} | "
                f"Strategy: {t.get('strategy_name', 'N/A')} | "
                f"Entry: {t.get('entry_price', 0):.2f} | Exit: {t.get('exit_price', 0):.2f} | "
                f"PnL: {t.get('pnl_usdt', 0):.2f} USDT ({t.get('pnl_pct', 0):.2f}%) | "
                f"Reason: {t.get('entry_reason', 'N/A')} -> {t.get('exit_reason', 'N/A')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _extract_recommendations(content: str) -> list[str]:
        """Extract recommendation bullet points from the AI response."""
        recommendations: list[str] = []
        in_reco_section = False
        for line in content.split("\n"):
            stripped = line.strip()
            if "## Recommendations" in stripped or "## Recommendation" in stripped:
                in_reco_section = True
                continue
            if in_reco_section:
                if stripped.startswith("##"):
                    break  # Next section
                if stripped.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")):
                    # Clean the bullet
                    clean = stripped.lstrip("-*0123456789. ").strip()
                    if clean:
                        recommendations.append(clean)
        return recommendations

    def _report_to_dict(self, report: AIReport) -> dict[str, Any]:
        """Convert an AIReport ORM object to a response dict."""
        metrics = {}
        if report.metrics_json:
            try:
                metrics = json.loads(report.metrics_json)
            except json.JSONDecodeError:
                pass

        return {
            "id": report.id,
            "title": f"AI Report - {report.report_type}",
            "content": report.content,
            "model_used": report.model_used,
            "total_trades_analysed": metrics.get("total_trades", 0),
            "win_rate": metrics.get("win_rate"),
            "total_pnl_usdt": metrics.get("total_pnl_usdt"),
            "recommendations": metrics.get("recommendations", []),
            "status": "completed",
            "progress_pct": 100.0,
            "created_at": report.created_at.isoformat() if report.created_at else "",
            "generation_time_seconds": metrics.get("generation_time_seconds", 0.0),
        }

    async def _call_openrouter(self, messages: list[dict]) -> str:
        """Send a chat completion request to OpenRouter."""
        if not self._api_key:
            return "[Error] OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable."

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kairos.prozentia.com",
            "X-Title": "Kairos Trading",
        }

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self.OPENROUTER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"[Error] Failed to generate report: {exc}"
