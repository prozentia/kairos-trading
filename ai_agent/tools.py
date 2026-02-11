"""AI Agent tools - Function calling definitions and execution.

Each tool maps to a Kairos API endpoint. The LLM picks which tool(s) to
call based on the user's question, and this module executes the HTTP
request and returns the result.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 30.0  # seconds

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_bot_status",
            "description": "Get current bot state: running/stopped, active positions, mode (live/dry-run), uptime.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trade_history",
            "description": "Get trade history with optional filters. Returns a list of completed trades.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Filter by trading pair, e.g. BTCUSDT",
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Filter by strategy name",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of past days to include (default: 7)",
                        "default": 7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of trades to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trade_stats",
            "description": "Get aggregated trading statistics: win rate, total P&L, average trade, best/worst trade, Sharpe ratio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Filter by pair"},
                    "strategy": {"type": "string", "description": "Filter by strategy"},
                    "days": {
                        "type": "integer",
                        "description": "Number of past days (default: 30)",
                        "default": 30,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio",
            "description": "Get portfolio overview: total balance, available balance, positions, exposure, daily P&L.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_analysis",
            "description": "Get technical analysis for a pair across multiple timeframes. Includes indicators, support/resistance, trend direction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Trading pair, e.g. BTCUSDT",
                        "default": "BTCUSDT",
                    },
                    "timeframes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Timeframes to analyse, e.g. ['1m', '5m', '1h']",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_strategies",
            "description": "List all available trading strategies with their status (active/inactive).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_strategy_detail",
            "description": "Get detailed information about a specific strategy: conditions, indicators, parameters, performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {
                        "type": "integer",
                        "description": "ID of the strategy",
                    },
                },
                "required": ["strategy_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "Launch a backtest for a strategy on historical data. Returns performance metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {
                        "type": "integer",
                        "description": "ID of the strategy to backtest",
                    },
                    "pair": {
                        "type": "string",
                        "description": "Trading pair (default: BTCUSDT)",
                        "default": "BTCUSDT",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of historical data (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["strategy_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "Get active price or indicator alerts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Filter by pair"},
                    "status": {
                        "type": "string",
                        "description": "Filter by status: active, triggered, expired",
                        "enum": ["active", "triggered", "expired"],
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_alert",
            "description": "Create a new price alert.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Trading pair, e.g. BTCUSDT"},
                    "condition": {
                        "type": "string",
                        "description": "Condition: above or below",
                        "enum": ["above", "below"],
                    },
                    "price": {"type": "number", "description": "Target price"},
                    "message": {"type": "string", "description": "Alert message (optional)"},
                },
                "required": ["pair", "condition", "price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_metrics",
            "description": "Get current risk metrics: drawdown, exposure, daily loss, max positions used, risk score.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

# Map tool names to their API endpoint and HTTP method
_TOOL_ROUTES: dict[str, tuple[str, str]] = {
    "get_bot_status":      ("GET",  "/bot/status"),
    "get_trade_history":   ("GET",  "/trades/"),
    "get_trade_stats":     ("GET",  "/trades/stats"),
    "get_portfolio":       ("GET",  "/portfolio/"),
    "get_market_analysis": ("GET",  "/market/analysis"),
    "list_strategies":     ("GET",  "/strategies/"),
    "get_strategy_detail": ("GET",  "/strategies/{strategy_id}"),
    "get_alerts":          ("GET",  "/alerts/"),
    "create_alert":        ("POST", "/alerts/"),
    "run_backtest":        ("POST", "/backtests/"),
    "get_risk_metrics":    ("GET",  "/portfolio/risk"),
}


async def execute_tool(
    tool_name: str,
    args: dict[str, Any],
    *,
    api_base_url: str,
    api_token: str,
) -> dict[str, Any]:
    """Execute a tool by calling the corresponding Kairos API endpoint.

    Args:
        tool_name: Name of the tool to execute.
        args: Arguments provided by the LLM.
        api_base_url: Base URL of the Kairos API.
        api_token: Internal authentication token.

    Returns:
        The JSON response from the API as a dict.

    Raises:
        ValueError: If the tool name is unknown.
        httpx.HTTPStatusError: If the API returns an error status.
    """
    route = _TOOL_ROUTES.get(tool_name)
    if route is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    method, path_template = route

    # Substitute path parameters (e.g. {strategy_id})
    path = path_template
    path_params = [p.strip("{}") for p in path_template.split("/") if p.startswith("{")]
    for param in path_params:
        value = args.pop(param, "")
        path = path.replace(f"{{{param}}}", str(value))

    url = f"{api_base_url.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        if method == "GET":
            # Pass remaining args as query parameters
            resp = await client.get(url, params=args or None, headers=headers)
        else:
            # POST: send args as JSON body
            resp = await client.post(url, json=args, headers=headers)

        resp.raise_for_status()
        return resp.json()
