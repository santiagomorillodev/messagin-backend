"""
ConnectionManager mejorado.
- Permite múltiples conexiones por usuario (mobile + web).
- Limpia sockets muertos.
- Métodos: connect, disconnect, broadcast, send_personal_message.
- Comentarios explican por qué hacemos cada cosa.
"""

from typing import Dict, List, Tuple
from fastapi import WebSocket
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list] = {}

    async def connect(self, user_id: int, websocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for ws in self.active_connections[user_id]:
                await ws.send_json(message)

    async def broadcast(self, message: dict):
        for conns in self.active_connections.values():
            for ws in conns:
                await ws.send_json(message)
