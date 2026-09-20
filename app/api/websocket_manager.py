"""Minimal WebSocket broadcast manager.

One instance per "channel" (scanner, prices, positions). Kept deliberately
simple — an in-process set of connections — since this is a single-instance
deployment; a multi-instance deployment would swap this for a Redis pub/sub
backed implementation behind the same ``broadcast``/``connect`` interface.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: Any) -> None:
        if not self._connections:
            return
        dead: list[WebSocket] = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 - any send failure means this client is gone
                dead.append(websocket)
        if dead:
            async with self._lock:
                for websocket in dead:
                    self._connections.discard(websocket)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


scanner_manager = ConnectionManager()
price_manager = ConnectionManager()
position_manager = ConnectionManager()
