"""
Admin route dependencies
"""
from typing import Dict
from fastapi import HTTPException, status, Depends, Request, Cookie
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routes.auth import get_current_user
from app.core.logging_config import logger


def require_admin(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Dependency to require admin privileges
    Supports both Cognito authentication and session-based admin login
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user from get_current_user (Cognito)
        db: Database session
        
    Returns:
        User dictionary if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    # First, try session-based admin authentication
    admin_user_id = request.cookies.get("admin_user_id")
    admin_session = request.cookies.get("admin_session")
    
    if admin_user_id and admin_session:
        # Session-based admin authentication
        try:
            from app.db.models import UserProfile
            user_id = int(admin_user_id)
            user = db.query(UserProfile).filter(
                UserProfile.id == user_id,
                UserProfile.isadmin == True,
                UserProfile.is_active == True
            ).first()
            
            if user:
                return {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "isadmin": user.isadmin
                }
        except (ValueError, Exception) as e:
            logger.warning(f"Invalid admin session: {str(e)}")
    
    # Fall back to Cognito authentication
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if not current_user.get("isadmin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

