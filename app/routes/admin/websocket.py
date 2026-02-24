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
        
        # 1. Collect all possible credentials
        query_params = dict(websocket.query_params)
        access_token = query_params.get('token')
        
        cookie_header = websocket.headers.get('cookie', '')
        cookies = {}
        if cookie_header:
            try:
                for item in cookie_header.split(';'):
                    if '=' in item:
                        k, v = item.split('=', 1)
                        cookies[k.strip()] = v.strip()
            except Exception as e:
                logger.warning(f"Error parsing cookies: {str(e)}")

        if not access_token:
            access_token = cookies.get('access_token')
            
        admin_user_id = cookies.get('admin_user_id')
        admin_session = cookies.get('admin_session')
        
        user = None
        
        # 2. Try Admin Session authentication first
        if admin_user_id and admin_session:
            try:
                from app.db.models import UserProfile
                u_id = int(admin_user_id)
                user = db.query(UserProfile).filter(
                    UserProfile.id == u_id,
                    UserProfile.isadmin == True,
                    UserProfile.is_active == True
                ).first()
            except Exception as e:
                logger.warning(f"Admin session auth failed: {str(e)}")
                
        # 3. Try Cognito/Access Token as fallback
        if not user and access_token:
            try:
                from app.core.security import decode_access_token
                token_data = decode_access_token(access_token)
                
                if not token_data.get("error"):
                    from app.db.models import UserProfile
                    user = db.query(UserProfile).filter(
                        UserProfile.username == token_data.get("sub")
                    ).first()
            except Exception as e:
                logger.warning(f"Token auth failed: {str(e)}")
        
        # 4. Final authorization check
        if not user or not user.isadmin or not user.is_active:
            # We must accept before we can close with a custom code in some environments
            # but Starlette allows closing before accept. To be safe:
            # The connection has already been accepted at the start of the function.
            await websocket.close(code=1008, reason="Admin access required")
            return
            
        # 5. Success - Proceed with connection
        # The connection has already been accepted at the start of the function.
        # This check is redundant if accept() was called at the beginning.
        # if websocket.client_state.name == "CONNECTING":
        #     await websocket.accept()
        
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

