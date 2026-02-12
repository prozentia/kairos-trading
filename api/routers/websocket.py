"""WebSocket router - live market data, position updates, logs, notifications.

Provides real-time streaming via WebSocket connections.  In production,
data is pushed by the engine and market adapter through the ConnectionManager.
The ConnectionManager also supports Redis pub/sub for multi-process setups.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections grouped by channel.

    Supports optional Redis pub/sub for broadcasting across multiple
    API server processes.
    """

    def __init__(self) -> None:
        # channel_name -> set of connected websockets
        self._channels: dict[str, set[WebSocket]] = {}
        self._redis = None

    async def init_redis(self) -> None:
        """Initialize Redis pub/sub if REDIS_URL is configured."""
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url)
        except Exception:
            self._redis = None

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept and register a websocket to a channel."""
        await websocket.accept()
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Remove a websocket from a channel."""
        if channel in self._channels:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]

    async def broadcast(self, channel: str, data: dict[str, Any]) -> None:
        """Send data to all connections on a channel."""
        message = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in self._channels.get(channel, set()):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)

        # Also publish to Redis for cross-process broadcasting
        if self._redis:
            try:
                await self._redis.publish(channel, message)
            except Exception:
                pass

    async def send_personal(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Send data to a single connection."""
        await websocket.send_text(json.dumps(data))

    @property
    def channel_count(self) -> int:
        """Return the number of active channels."""
        return len(self._channels)

    @property
    def connection_count(self) -> int:
        """Return the total number of active connections."""
        return sum(len(conns) for conns in self._channels.values())


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Market price stream
# ---------------------------------------------------------------------------

@router.websocket("/ws/market/{pair}")
async def ws_market(websocket: WebSocket, pair: str):
    """Live price stream for a trading pair.

    Sends: {"pair": "BTCUSDT", "price": 98250.5, "timestamp": "..."}

    The client connects and stays alive.  Price updates are pushed
    via manager.broadcast() from the market data adapter.
    Clients can send "ping" messages to keep the connection alive.
    """
    channel = f"market:{pair.upper()}"
    await manager.connect(websocket, channel)
    try:
        while True:
            # Keep connection alive; actual data pushed via manager.broadcast()
            data = await websocket.receive_text()
            # Client can send ping / subscribe messages
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


# ---------------------------------------------------------------------------
# Trade notifications
# ---------------------------------------------------------------------------

@router.websocket("/ws/trades")
async def ws_trades(websocket: WebSocket):
    """Real-time trade notifications (opened, closed, updated).

    Sends: {"event": "trade_opened" | "trade_closed", "data": {...}}
    """
    channel = "trades"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


# ---------------------------------------------------------------------------
# Bot status stream
# ---------------------------------------------------------------------------

@router.websocket("/ws/bot-status")
async def ws_bot_status(websocket: WebSocket):
    """Stream bot status updates (running state, signal events).

    Sends: {"event": "status_update", "data": {"running": true, ...}}
    """
    channel = "bot-status"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


# ---------------------------------------------------------------------------
# Position updates
# ---------------------------------------------------------------------------

@router.websocket("/ws/positions")
async def ws_positions(websocket: WebSocket):
    """Real-time position updates (open, close, PnL changes).

    Sends: {"event": "position_update", "data": {...}}
    """
    channel = "positions"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


# ---------------------------------------------------------------------------
# Log stream
# ---------------------------------------------------------------------------

@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    """Stream bot logs in real time.

    Sends: {"level": "INFO", "message": "...", "timestamp": "..."}
    """
    channel = "logs"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    """Real-time notifications (alerts triggered, trade events, errors).

    Sends: {"type": "alert_triggered" | "trade_opened" | "trade_closed" | "error",
            "data": {...}, "timestamp": "..."}
    """
    channel = "notifications"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
