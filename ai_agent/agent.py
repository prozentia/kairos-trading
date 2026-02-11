"""Kairos AI Agent - Main agent class.

Manages conversation flow: receives user messages, builds LLM context,
calls OpenRouter with tool definitions, executes tool calls, and returns
the final response.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ai_agent.config import AgentConfig
from ai_agent.provider import OpenRouterProvider
from ai_agent.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)


class KairosAgent:
    """Conversational AI agent backed by OpenRouter LLM."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.provider = OpenRouterProvider(
            api_key=config.openrouter_api_key,
            default_model=config.openrouter_model,
        )
        # Per-user conversation history: user_id -> list of messages
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def chat(self, message: str, user_id: str) -> str:
        """Process a user message and return the agent's text response.

        Steps:
        1. Append user message to history.
        2. Build full message list (system + history).
        3. Call LLM via OpenRouter.
        4. If the LLM requests tool calls, execute them and loop.
        5. Return the final assistant text.
        """
        self._history[user_id].append({"role": "user", "content": message})
        self._trim_history(user_id)

        messages = self._build_messages(user_id)

        # Tool-call loop (max 5 iterations to avoid infinite loops)
        for _ in range(5):
            try:
                response = await self._call_llm(messages)
            except Exception:
                logger.exception("LLM call failed")
                return "Erreur lors de la communication avec le LLM. Reessayez."

            # Check for tool calls
            tool_calls = response.get("tool_calls")
            if not tool_calls:
                break

            # Execute each tool call and append results
            tool_results = await self._handle_tool_calls(tool_calls)
            messages.append({"role": "assistant", "tool_calls": tool_calls})
            for result in tool_results:
                messages.append(result)
        else:
            logger.warning("Tool-call loop hit max iterations for user %s", user_id)

        # Extract final text
        assistant_text = response.get("content", "")
        if not assistant_text:
            assistant_text = "Je n'ai pas pu generer de reponse. Reessayez."

        # Save assistant reply to history
        self._history[user_id].append({"role": "assistant", "content": assistant_text})
        self._trim_history(user_id)

        return assistant_text

    def clear_history(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        self._history.pop(user_id, None)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _build_messages(self, user_id: str) -> list[dict[str, Any]]:
        """Build the full message list: system prompt + conversation history."""
        system_prompt = self._get_system_prompt()
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(self._history[user_id])
        return messages

    async def _call_llm(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Call OpenRouter and return the parsed response.

        Returns a dict with at least 'content' (str) and optionally
        'tool_calls' (list of tool call dicts).
        """
        result = await self.provider.complete(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            model=self.config.openrouter_model,
        )
        return result

    async def _handle_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Execute tool calls and return tool-result messages for the LLM."""
        results: list[dict[str, Any]] = []
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            tool_args = tc.get("function", {}).get("arguments", {})
            tool_call_id = tc.get("id", "")

            logger.info("Executing tool: %s(%s)", tool_name, tool_args)
            try:
                output = await execute_tool(
                    tool_name,
                    tool_args,
                    api_base_url=self.config.api_base_url,
                    api_token=self.config.internal_api_token,
                )
            except Exception as exc:
                logger.exception("Tool %s failed", tool_name)
                output = {"error": str(exc)}

            results.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": str(output),
            })
        return results

    def _get_system_prompt(self) -> str:
        """Build the system prompt with current context."""
        return self.config.system_prompt

    def _trim_history(self, user_id: str) -> None:
        """Keep only the last *max_history* messages per user."""
        max_len = self.config.max_history * 2  # user + assistant pairs
        history = self._history[user_id]
        if len(history) > max_len:
            self._history[user_id] = history[-max_len:]
