"""
Authentication routes for Manual Auth integration
"""
import os
from typing import Optional, Dict
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, HTTPException, status, Cookie, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from app.db.session import get_db
from app.db.models import UserProfile, AnonymousUsers, KYCStatus
from app.core.config import settings
from app.core.logging_config import logger
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


@router.get("/login")
async def login_page(request: Request):
    """Render custom login page"""
    from app.core.templates import templates
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "login_url": settings.LOGIN_URL}
    )


@router.get("/signup")
async def signup_page(request: Request):
    """Render custom signup page"""
    from app.core.templates import templates
    return templates.TemplateResponse(
        "auth/signup.html",
        {"request": request, "signup_url": settings.SIGNUP_URL}
    )


def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get current authenticated user
    """
    if not access_token:
        access_token = request.cookies.get('access_token')
    
    if not access_token:
        return {"error": 401, "message": "Not authenticated"}
    
    # Decode token
    token_data = decode_access_token(access_token)
    
    if not token_data or token_data.get("error"):
        return {"error": 401, "message": "Invalid or expired token"}
    
    # Get user from database
    try:
        user = db.query(UserProfile).filter(
            UserProfile.username == token_data["sub"]
        ).one()
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "isadmin": user.isadmin
        }
    except NoResultFound:
        return {"error": 404, "message": "User not found"}
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return {"error": 500, "message": "Internal error"}


@router.post("/api/signup")
async def api_signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    firstname: str = Form(...),
    lastname: str = Form(...),
    db: Session = Depends(get_db)
):
    """Manual signup API"""
    username = username.strip()
    email = email.strip().lower()
    logger.info(f"Signup attempt for: {username} ({email})")
    try:
        # Check if user already exists
        existing_user = db.query(UserProfile).filter(
            (UserProfile.username == username) | (UserProfile.email == email)
        ).first()
        
        if existing_user:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "Username or email already exists"}
            )
        
        # Create new user
        new_user = UserProfile(
            username=username,
            email=email,
            firstname=firstname,
            lastname=lastname,
            hashed_password=get_password_hash(password),
            is_active=True,
            isadmin=False,
            kyc_status=KYCStatus.NOT_SUBMITTED
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User successfully created: {username}")
        
        # Create access token
        access_token = create_access_token(data={"sub": username, "email": email})
        
        response = JSONResponse({
            "success": True, 
            "message": "User registered successfully",
            "redirect_url": "/"
        })
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax",
            max_age=60*60*24*7 # 7 days
        )
        response.set_cookie(
            key="username",
            value=f"{firstname} {lastname}",
            httponly=True
        )
        
        return response
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Signup error: {error_msg}", exc_info=True)
        
        # Check for specific database errors
        if "UNIQUE constraint failed" in error_msg:
            message = "Username or email already exists."
        elif "NOT NULL constraint failed" in error_msg:
            message = "Please fill in all required fields."
        else:
            message = "Failed to create user. Please try again later."
            
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": message}
        )


@router.post("/api/login")
async def api_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Manual login API"""
    try:
        # Get user
        user = db.query(UserProfile).filter(UserProfile.username == username).first()
        
        if not user or not verify_password(password, user.hashed_password):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": "Invalid username or password"}
            )
        
        if not user.is_active:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "message": "Account is inactive"}
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user.username, "email": user.email})
        
        redirect_url = "/admin/dashboard" if user.isadmin else "/"
        
        response = JSONResponse({
            "success": True, 
            "message": "Login successful",
            "redirect_url": redirect_url
        })
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax",
            max_age=60*60*24*7 # 7 days
        )
        response.set_cookie(
            key="username",
            value=f"{user.firstname} {user.lastname}",
            httponly=True
        )
        
        logger.info(f"User logged in: {username}")
        return response
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": "An error occurred during login"}
        )


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="username")
    return response


@router.post("/update-phone")
async def update_phone(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update user phone number"""
    try:
        if current_user.get("error"):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        user_id = current_user.get("user_id")
        body = await request.json()
        phone = body.get("phone", "").strip()
        
        if not phone or len(phone) != 10 or not phone.isdigit():
            raise HTTPException(status_code=400, detail="Invalid phone number")
        
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.phone = phone
        db.commit()
        return {"success": True, "message": "Phone updated"}
    except Exception as e:
        logger.error(f"Phone update error: {str(e)}")
        raise HTTPException(status_code=500, detail="Update failed")


@router.post("/kyc/upload")
async def upload_kyc_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upload KYC document"""
    from app.services.kyc_service import kyc_service
    from datetime import datetime
    
    try:
        if current_user.get("error"):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        user_id = current_user.get("user_id")
        file_url = await kyc_service.upload_kyc_document(db, user_id, document_type, file)
        
        return JSONResponse({
            "success": True,
            "document_type": document_type,
            "file_url": file_url,
            "uploaded_at": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"KYC upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")
