"""
WebSocket connection manager for real-time frame streaming.
"""
import logging
import json
from typing import Set, List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasting.
    Used for real-time detection streaming.
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """Accept and register WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected: user={user_id}, total={len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected: user={user_id}, total={len(self.active_connections)}")
    
    async def broadcast_detection(
        self,
        user_id: int,
        detection_data: Dict[str, Any],
    ) -> None:
        """
        Broadcast detection result to user's connections.
        
        Args:
            user_id: User to broadcast to
            detection_data: Detection result data
        """
        if user_id not in self.user_connections:
            return
        
        message = {
            "type": "detection",
            "data": detection_data,
        }
        
        disconnected = []
        
        for connection in list(self.user_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send detection to user {user_id}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            await self.disconnect(connection, user_id)
    
    async def broadcast_frame_result(
        self,
        user_id: int,
        device_id: int,
        frame_data: Dict[str, Any],
    ) -> None:
        """
        Broadcast frame detection result.
        
        Args:
            user_id: User to broadcast to
            device_id: Source device ID
            frame_data: Frame detection data
        """
        message = {
            "type": "frame_result",
            "device_id": device_id,
            "data": frame_data,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        
        await self.broadcast_detection(user_id, message)
    
    async def send_to_user(
        self,
        user_id: int,
        message: Dict[str, Any],
    ) -> None:
        """Send message to all user's connections."""
        if user_id not in self.user_connections:
            return
        
        disconnected = []
        
        for connection in list(self.user_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                disconnected.append(connection)
        
        for connection in disconnected:
            await self.disconnect(connection, user_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connections."""
        disconnected = []
        
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Broadcast failed: {e}")
                disconnected.append(connection)
        
        # Note: Can't disconnect without user_id, just let them time out
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for user."""
        return len(self.user_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total active connections."""
        return len(self.active_connections)


# Global connection manager instance
manager = ConnectionManager()


async def handle_websocket_connection(
    websocket: WebSocket,
    user_id: int,
) -> None:
    """
    Handle WebSocket connection lifecycle.
    
    Usage in routes:
        @app.websocket("/ws/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: int):
            await handle_websocket_connection(websocket, user_id)
    """
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            message_type = message.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif message_type == "subscribe":
                # Client subscribed to specific device
                device_id = message.get("device_id")
                logger.info(f"User {user_id} subscribed to device {device_id}")
            elif message_type == "unsubscribe":
                device_id = message.get("device_id")
                logger.info(f"User {user_id} unsubscribed from device {device_id}")
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnect: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, user_id)
