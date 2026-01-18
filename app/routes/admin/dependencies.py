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
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Dependency to require admin privileges
    
    Args:
        current_user: Current authenticated user from get_current_user
        db: Database session
        
    Returns:
        User dictionary if admin
        
    Raises:
        HTTPException: If user is not admin
    """
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

