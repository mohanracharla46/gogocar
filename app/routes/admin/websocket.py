"""
WebSocket routes for admin notifications
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import get_db
from app.utils.websocket_manager import websocket_manager
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/ws",
    tags=["admin-websocket"]
)


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for admin notifications
    
    Only authenticated admin users can connect.
    Sends real-time notifications for new bookings and support tickets.
    """
    db = next(get_db())
    try:
        # Accept connection first (required before we can send/close)
        await websocket.accept()
        
        # Get access token from cookies in query string or headers
        # WebSocket doesn't support Cookie() dependency, so we need to get it manually
        access_token = None
        user = None
        
        # Try to get from query parameters (client can pass it)
        query_params = dict(websocket.query_params)
        if 'token' in query_params:
            access_token = query_params['token']
        else:
            # Try to get from cookies in headers
            cookie_header = websocket.headers.get('cookie', '')
            cookies = {}
            if cookie_header:
                cookies = dict(item.split('=', 1) for item in cookie_header.split('; ') if '=' in item)
                access_token = cookies.get('access_token')
            
            # Admin specific session cookies
            admin_user_id = cookies.get('admin_user_id')
            admin_session = cookies.get('admin_session')
            
            if admin_user_id and admin_session:
                # Authenticate via admin session
                try:
                    from app.db.models import UserProfile
                    u_id = int(admin_user_id)
                    user = db.query(UserProfile).filter(
                        UserProfile.id == u_id,
                        UserProfile.isadmin == True,
                        UserProfile.is_active == True
                    ).first()
                except:
                    pass
                
        if not user and access_token:
            # Fall back to access_token (Cognito)
            from app.core.security import decode_access_token
            token_data = decode_access_token(access_token)
            
            if not token_data.get("error"):
                from app.db.models import UserProfile
                user = db.query(UserProfile).filter(
                    UserProfile.username == token_data.get("sub")
                ).first()
        
        if not user or not user.isadmin or not user.is_active:
            await websocket.close(code=1008, reason="Admin access required")
            db.close()
            return
        
        # Register the connection (connection already accepted above)
        await websocket_manager.connect(websocket, user.id)
        
        # Send welcome message
        try:
            await websocket_manager.send_personal_message({
                "type": "connected",
                "message": "Connected to notification service"
            }, websocket)
        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")
            websocket_manager.disconnect(websocket)
            db.close()
            return
        
        # Keep connection alive and handle messages
        try:
            while True:
                # Wait for any message from client (ping/pong)
                data = await websocket.receive_text()
                # Echo back or handle ping
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            websocket_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        db.close()

