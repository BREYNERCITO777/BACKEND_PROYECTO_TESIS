"""Conexiones WebSocket del panel y difusión de alertas en tiempo real."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import WebSocket


class WebSocketManager:
    """Registro de los paneles conectados por WebSocket."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Acepta la conexión y la registra para recibir alertas."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Deja de enviar alertas a esa conexión."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: Dict[str, Any]):
        """Envía el mensaje a todos los paneles y descarta las conexiones caídas."""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


ws_manager = WebSocketManager()
