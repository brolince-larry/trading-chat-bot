"""WebSocket endpoints. Each is a one-way broadcast channel driven by the
background loop in ``app.api.background`` — clients connect and receive
periodic updates; anything a client sends is ignored (used only to detect
disconnects via ``receive_text``).
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websocket_manager import (
    notification_manager,
    position_manager,
    price_manager,
    scanner_manager,
)

router = APIRouter()


@router.websocket("/ws/scanner")
async def ws_scanner(websocket: WebSocket) -> None:
    await scanner_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await scanner_manager.disconnect(websocket)


@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket) -> None:
    await price_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await price_manager.disconnect(websocket)


@router.websocket("/ws/positions")
async def ws_positions(websocket: WebSocket) -> None:
    await position_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await position_manager.disconnect(websocket)


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket) -> None:
    await notification_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await notification_manager.disconnect(websocket)
