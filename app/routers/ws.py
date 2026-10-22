"""Canal WebSocket por el que el panel recibe las alertas."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import ws_manager


router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/alerts")
async def websocket_alerts(websocket: WebSocket):
    """Mantiene abierto el canal por el que el panel recibe las alertas."""
    await ws_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

    except Exception:
        ws_manager.disconnect(websocket)
