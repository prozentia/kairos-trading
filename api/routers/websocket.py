"""WebSocket router - live market data, position updates, logs, notifications."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections grouped by channel."""

    def __init__(self) -> None:
        # channel_name -> set of connected websockets
        self._channels: dict[str, set[WebSocket]] = {}

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

    async def send_personal(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Send data to a single connection."""
        await websocket.send_text(json.dumps(data))


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Market price stream
# ---------------------------------------------------------------------------

@router.websocket("/ws/market/{pair}")
async def ws_market(websocket: WebSocket, pair: str):
    """Live price stream for a trading pair.

    Sends: {"pair": "BTCUSDT", "price": 98250.5, "timestamp": "..."}
    """
    channel = f"market:{pair.upper()}"
    await manager.connect(websocket, channel)
    try:
        while True:
            # Keep connection alive; actual data pushed via manager.broadcast()
            data = await websocket.receive_text()
            # Client can send ping / subscribe messages
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
            await websocket.receive_text()
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
            await websocket.receive_text()
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
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
