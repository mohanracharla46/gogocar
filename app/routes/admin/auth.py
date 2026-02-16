"""
Admin authentication routes (separate from Cognito)
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib
import secrets
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import UserProfile
from app.core.templates import templates
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/auth",
    tags=["admin-auth"]
)


class AdminLoginRequest(BaseModel):
    """Admin login request schema"""
    username: str
    password: str
    remember: bool = False


from app.core.security import verify_password

def verify_admin_credentials(username: str, password: str, db: Session) -> UserProfile:
    """
    Verify admin credentials using secure hashing
    """
    user = db.query(UserProfile).filter(
        UserProfile.username == username,
        UserProfile.isadmin == True,
        UserProfile.is_active == True
    ).first()
    
    if not user or not user.hashed_password:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request}
    )


@router.post("/login")
async def admin_login(
    request: Request,
    login_data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """Handle admin login"""
    try:
        # Verify credentials
        user = verify_admin_credentials(login_data.username, login_data.password, db)
        
        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "message": "Invalid username or password"
                }
            )
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Create response
        response = JSONResponse(
            content={
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "email": user.email
                }
            }
        )
        
        # Set session cookie
        max_age = 30 * 24 * 60 * 60 if login_data.remember else 24 * 60 * 60  # 30 days or 1 day
        
        response.set_cookie(
            key="admin_session",
            value=session_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=max_age
        )
        
        # Store user info in cookie for easy access
        response.set_cookie(
            key="admin_user_id",
            value=str(user.id),
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=max_age
        )
        
        response.set_cookie(
            key="admin_username",
            value=user.username,
            httponly=False,  # Allow JS to read for display
            secure=False,
            samesite="lax",
            max_age=max_age
        )
        
        logger.info(f"Admin user {user.username} logged in successfully")
        
        return response
        
    except Exception as e:
        logger.error(f"Error during admin login: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An error occurred during login"
            }
        )


@router.get("/logout")
async def admin_logout(request: Request):
    """Admin logout"""
    response = RedirectResponse(url="/admin/auth/login", status_code=302)
    response.delete_cookie(key="admin_session")
    response.delete_cookie(key="admin_user_id")
    response.delete_cookie(key="admin_username")
    
    logger.info("Admin user logged out")
    return response


def get_admin_user(
    request: Request,
    db: Session = Depends(get_db)
) -> UserProfile:
    """
    Dependency to get current admin user from session
    """
    admin_user_id = request.cookies.get("admin_user_id")
    admin_session = request.cookies.get("admin_session")
    
    if not admin_user_id or not admin_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        user_id = int(admin_user_id)
        user = db.query(UserProfile).filter(
            UserProfile.id == user_id,
            UserProfile.isadmin == True,
            UserProfile.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )


def require_admin_session(
    current_user: UserProfile = Depends(get_admin_user)
) -> dict:
    """
    Dependency to require admin session (alternative to Cognito-based require_admin)
    """
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "firstname": current_user.firstname,
        "lastname": current_user.lastname,
        "isadmin": current_user.isadmin
    }
