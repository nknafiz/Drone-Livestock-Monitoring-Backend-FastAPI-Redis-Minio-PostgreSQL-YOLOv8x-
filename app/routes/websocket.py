"""
WebSocket endpoint for real-time detection streaming.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.ws.manager import manager, handle_websocket_connection
from app.auth.jwt_handler import JWTService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/detection/{user_id}")
async def websocket_detection_endpoint(websocket: WebSocket, user_id: int) -> None:
    """
    WebSocket endpoint for real-time detection results streaming.
    
    Connect with: ws://localhost:8000/ws/detection/{user_id}
    
    Message types:
    - Subscribe: {"type": "subscribe", "device_id": 1}
    - Unsubscribe: {"type": "unsubscribe", "device_id": 1}
    - Ping: {"type": "ping"}
    
    Receive:
    - Detection result: {"type": "frame_result", "device_id": 1, "data": {...}, "timestamp": "..."}
    - Pong: {"type": "pong"}
    """
    try:
        # Extract and verify token from query params (optional, for better security)
        query_params = websocket.query_params
        token = query_params.get("token")
        
        if token:
            # Verify token (optional security layer)
            payload = JWTService.verify_token(token)
            if not payload or int(payload.get("sub")) != user_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                logger.warning(f"WebSocket auth failed for user {user_id}")
                return
        
        # Connect user
        await manager.connect(websocket, user_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to detection stream",
            "user_id": user_id,
        })
        
        # Handle messages
        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "subscribe":
                    device_id = data.get("device_id")
                    logger.info(f"User {user_id} subscribed to device {device_id}")
                    await websocket.send_json({
                        "type": "subscribed",
                        "device_id": device_id,
                    })
                
                elif message_type == "unsubscribe":
                    device_id = data.get("device_id")
                    logger.info(f"User {user_id} unsubscribed from device {device_id}")
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "device_id": device_id,
                    })
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
        
        except WebSocketDisconnect:
            await manager.disconnect(websocket, user_id)
            logger.info(f"WebSocket disconnect: user={user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.disconnect(websocket, user_id)
        except:
            pass


# Helper function to broadcast detection result to user
async def broadcast_detection_to_user(
    user_id: int,
    device_id: int,
    detection_result: dict,
) -> None:
    """
    Broadcast detection result to user's WebSocket connections.
    
    Usage:
        await broadcast_detection_to_user(
            user_id=1,
            device_id=1,
            detection_result={
                "animal_count": 5,
                "confidence_score": 0.85,
                "bounding_boxes": [...]
            }
        )
    """
    await manager.broadcast_frame_result(
        user_id=user_id,
        device_id=device_id,
        frame_data=detection_result,
    )
