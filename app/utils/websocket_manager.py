"""
WebSocket manager for real-time notifications
"""
from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio
from app.core.logging_config import logger


class ConnectionManager:
    """Manages WebSocket connections for admin notifications"""
    
    def __init__(self):
        # Store active connections: {websocket: user_id}
        self.active_connections: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Register a WebSocket connection (connection should already be accepted)"""
        self.active_connections[websocket] = user_id
        logger.info(f"WebSocket connected: User {user_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            user_id = self.active_connections.pop(websocket)
            logger.info(f"WebSocket disconnected: User {user_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {str(e)}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected admins"""
        disconnected = []
        for websocket in self.active_connections.keys():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {str(e)}")
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_notification(self, notification_type: str, data: dict):
        """
        Send a notification to all connected admins
        
        Args:
            notification_type: Type of notification ('booking' or 'ticket')
            data: Notification data
        """
        message = {
            "type": "notification",
            "notification_type": notification_type,
            "data": data
        }
        await self.broadcast(message)


# Global instance
websocket_manager = ConnectionManager()

