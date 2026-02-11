"""OpenRouter LLM provider.

Handles HTTP communication with the OpenRouter API, including
request formatting, error handling, and retry logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_TIMEOUT = 120.0  # seconds
_MAX_RETRIES = 2


class OpenRouterProvider:
    """Async provider for OpenRouter chat completions."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "anthropic/claude-sonnet-4",
    ) -> None:
        self.api_key = api_key
        self.default_model = default_model

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request to OpenRouter.

        Returns a normalised dict:
            {
                "content": "...",           # assistant text (may be empty)
                "tool_calls": [...] | None, # tool call requests
                "model": "...",             # model actually used
                "usage": {...},             # token usage
            }
        """
        chosen_model = model or self.default_model
        payload = self._format_request(messages, tools, chosen_model)

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await self._send(payload)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                # Retry on 429 (rate limit) and 5xx (server errors)
                if status in (429, 500, 502, 503, 504) and attempt < _MAX_RETRIES:
                    logger.warning(
                        "OpenRouter returned %d, retrying (%d/%d)...",
                        status, attempt + 1, _MAX_RETRIES,
                    )
                    continue
                raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Request error: %s, retrying (%d/%d)...",
                        exc, attempt + 1, _MAX_RETRIES,
                    )
                    continue
                raise

        # Should not reach here, but just in case
        raise last_error  # type: ignore[misc]

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _format_request(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
    ) -> dict[str, Any]:
        """Build the JSON payload for the OpenRouter API."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send the request and parse the response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kairos.prozentia.com",
            "X-Title": "Kairos Trading AI Agent",
        }

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(_OPENROUTER_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return self._parse_response(data)

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> dict[str, Any]:
        """Normalise the OpenRouter response into a standard format."""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        # Parse tool calls if present
        tool_calls = message.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", "")
                if isinstance(args, str):
                    try:
                        fn["arguments"] = json.loads(args)
                    except json.JSONDecodeError:
                        fn["arguments"] = {}

        return {
            "content": message.get("content", "") or "",
            "tool_calls": tool_calls,
            "model": data.get("model", ""),
            "usage": data.get("usage", {}),
        }
