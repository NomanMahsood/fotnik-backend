from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            if websocket.client_state.value != 3:  # 3 is DISCONNECTED state
                await websocket.send_json(message)
            else:
                logger.warning("Attempted to send message to disconnected WebSocket")
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")

    async def broadcast(self, message: dict, client_id: str = None):
        if client_id:
            # Send to specific client's connections
            if client_id in self.active_connections:
                for connection in self.active_connections[client_id]:
                    try:
                        if connection.client_state.value != 3:  # 3 is DISCONNECTED state
                            await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to client {client_id}: {str(e)}")
        else:
            # Broadcast to all connections
            for connections in self.active_connections.values():
                for connection in connections:
                    try:
                        if connection.client_state.value != 3:  # 3 is DISCONNECTED state
                            await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting message: {str(e)}")

manager = ConnectionManager() 