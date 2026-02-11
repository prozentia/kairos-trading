"""AI report generator service - generates trading analysis via OpenRouter."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ReportGenerator:
    """Generates AI-powered trading analysis reports.

    Collects recent trade data, formats it as a prompt, sends it to an
    LLM via OpenRouter, and parses the structured response.
    """

    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "anthropic/claude-sonnet-4",
    ) -> None:
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self._model = model
        self._default_prompt = (
            "You are an expert crypto trading analyst. "
            "Analyse the following trades and provide actionable insights, "
            "a performance summary, and recommendations for improvement."
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        trades: list[dict[str, Any]],
        custom_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a full analysis report from trade data.

        Returns a dict with: title, content, recommendations, model_used,
        total_trades_analysed, win_rate, total_pnl_usdt.
        """
        prompt = custom_prompt or self._default_prompt

        # Format trades for the LLM
        trade_summary = self._format_trades(trades)

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Here are my recent trades:\n\n{trade_summary}\n\nPlease analyse."},
        ]

        # Call OpenRouter
        response = await self._call_openrouter(messages)

        return {
            "title": f"Trading Analysis - {len(trades)} trades",
            "content": response,
            "model_used": self._model,
            "total_trades_analysed": len(trades),
            "recommendations": [],  # TODO: parse structured recommendations
        }

    # ------------------------------------------------------------------
    # Prompt management
    # ------------------------------------------------------------------

    def get_prompt(self) -> str:
        """Return the current system prompt."""
        # TODO: read from config file / DB
        return self._default_prompt

    def set_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        # TODO: persist to config file / DB
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
                f"Entry: {t.get('entry_price', 0):.2f} | Exit: {t.get('exit_price', 0):.2f} | "
                f"PnL: {t.get('pnl_usdt', 0):.2f} USDT ({t.get('pnl_pct', 0):.2f}%) | "
                f"Reason: {t.get('entry_reason', 'N/A')} -> {t.get('exit_reason', 'N/A')}"
            )
        return "\n".join(lines)

    async def _call_openrouter(self, messages: list[dict]) -> str:
        """Send a chat completion request to OpenRouter."""
        if not self._api_key:
            return "[Error] OpenRouter API key not configured."

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

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.OPENROUTER_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
