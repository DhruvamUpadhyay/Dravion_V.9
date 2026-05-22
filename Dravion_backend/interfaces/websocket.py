import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from core.event_bus import event_bus
from core.logger import log
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.debug("websocket_connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        log.debug("websocket_disconnected", total_connections=len(self.active_connections))

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                log.error("websocket_send_error", error=str(e))

manager = ConnectionManager()

# We would register this to event bus in main.py
async def on_event(data: dict):
    await manager.broadcast(json.dumps(data))
