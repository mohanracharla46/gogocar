"""
Authentication routes for Cognito integration
"""
import os
import requests
from typing import Optional, Dict
from fastapi import APIRouter, Depends, Request, HTTPException, status, Cookie, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
import cognitojwt
import boto3

from app.db.session import get_db
from app.db.models import UserProfile, AnonymousUsers
from app.core.config import settings
from app.core.logging_config import logger
from app.utils.auth_utils import create_user_if_not_exists

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


def decode_token(token: str) -> Dict:
    """
    Decode and validate Cognito access token
    
    Args:
        token: Access token
        
    Returns:
        Decoded token data
    """
    try:
        decoded_token = cognitojwt.decode(
            token,
            "us-east-1",
            settings.USERPOOL_ID,
            settings.APP_CLIENT_ID
        )
        return {
            "username": decoded_token.get("username"),
            "email": decoded_token.get("email"),
            "sub": decoded_token.get("sub")
        }
    except cognitojwt.CognitoJWTException as e:
        logger.error(f"Cognito JWT exception: {str(e)}")
        return {"error": "Invalid token"}
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        return {"error": "Unable to decode token"}


def get_access_token(
    authorization_code: str,
    redirect_uri: str
) -> Optional[str]:
    """
    Get access token from Cognito
    
    Args:
        authorization_code: Authorization code
        redirect_uri: Redirect URI
        
    Returns:
        Access token or None
    """
    token_url = f"{settings.COGNITO_DOMAIN}/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.APP_CLIENT_ID,
        "client_secret": settings.APP_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "code": authorization_code,
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        
        if response.ok:
            return response.json().get("access_token")
        else:
            logger.error(f"Failed to get access token: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None


def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get current authenticated user
    
    Args:
        request: FastAPI request object
        access_token: Access token from cookie
        db: Database session
        
    Returns:
        User data dictionary
    """
    if not access_token:
        access_token = request.cookies.get('access_token')
    
    if not access_token:
        return {"error": 401, "message": "Not authenticated"}
    
    # Decode token
    token_data = decode_token(access_token)
    
    if token_data.get("error"):
        return {"error": 401, "message": "Invalid token"}
    
    # Get user from database
    try:
        user = db.query(UserProfile).filter(
            UserProfile.username == token_data["username"]
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
        # User not found - don't auto-create
        logger.warning(f"User not found in database: {token_data.get('username')}")
        return {"error": 404, "message": "User not found"}
    except MultipleResultsFound:
        logger.error(f"Multiple users found for username: {token_data['username']}")
        return {"error": 500, "message": "Multiple users found"}
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return {"error": 500, "message": "Database error"}


@router.get("/token")
async def get_token(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Cognito
    
    Args:
        request: FastAPI request object
        code: Authorization code
        db: Database session
        
    Returns:
        Redirect response with cookies set
    """
    try:
        # Get access token
        access_token = get_access_token(code, settings.REDIRECT_URI)
        
        if not access_token:
            logger.error("Failed to get access token")
            return RedirectResponse(url="/?error=auth_failed", status_code=status.HTTP_302_FOUND)
        
        # Decode token to get user info
        token_data = decode_token(access_token)
        
        if token_data.get("error"):
            logger.error("Failed to decode token")
            return RedirectResponse(url="/?error=token_invalid", status_code=status.HTTP_302_FOUND)
        
        # Get action from cookie (login or signup)
        action = request.cookies.get('auth_action', 'login')
        
        # Check if user exists
        user = db.query(UserProfile).filter(
            UserProfile.username == token_data.get("username")
        ).first()
        
        # Handle based on action
        if action == 'signup':
            # For signup: create user if not exists
            if not user:
                try:
                    user = create_user_if_not_exists(token_data, db)
                    logger.info(f"New user created during signup: {user.username}")
                except Exception as e:
                    logger.error(f"Error creating user during signup: {str(e)}")
                    response = RedirectResponse(url="/?error=server_error", status_code=status.HTTP_302_FOUND)
                    response.delete_cookie(key="auth_action")
                    return response
            else:
                logger.info(f"Existing user logged in via signup: {user.username}")
        else:
            # For login: user must exist
            if not user:
                logger.warning(f"Login attempted for non-existent user: {token_data.get('username')}")
                # Clear any cookies and redirect with error
                response = RedirectResponse(url="/?error=user_not_found", status_code=status.HTTP_302_FOUND)
                response.delete_cookie(key="auth_action")
                response.delete_cookie(key="access_token")
                response.delete_cookie(key="username")
                return response
            else:
                logger.info(f"User logged in: {user.username}")
        
        # Check for anonymous user session
        unique_string = request.cookies.get('unique_string')
        redirect_url = "/"
        
        # Check for return_url parameter (for pending bookings)
        return_url_param = request.query_params.get("return_url")
        if return_url_param:
            redirect_url = return_url_param
        
        if unique_string:
            anony_user = db.query(AnonymousUsers).filter(
                AnonymousUsers.unique_string == unique_string
            ).first()
            
            if anony_user:
                redirect_url = f"/cars/car-detail/{anony_user.car_id}?start_time={anony_user.start_time}&end_time={anony_user.end_time}&location={anony_user.location}"
                db.delete(anony_user)
                db.commit()
        
        # Redirect admin users (but only if no return_url specified)
        if user.isadmin and not return_url_param:
            redirect_url = "/admin/dashboard"
        
        # Create response with cookies
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax"
        )
        response.set_cookie(
            key="username",
            value=f"{user.firstname} {user.lastname}",
            httponly=True
        )
        # Clear the auth_action cookie
        response.delete_cookie(key="auth_action")
        
        logger.info(f"User authenticated: {user.username}")
        return response
        
    except Exception as e:
        logger.error(f"Error in token endpoint: {str(e)}")
        return RedirectResponse(url="/?error=server_error", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout(request: Request):
    """
    Logout user by clearing cookies
    
    Args:
        request: FastAPI request object
        
    Returns:
        Redirect response
    """
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="username")
    response.set_cookie(key="isloggedout", value="true", httponly=True)
    
    logger.info("User logged out")
    return response


@router.post("/update-phone")
async def update_phone(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update user phone number
    
    Args:
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        JSON response with success status
    """
    try:
        if current_user.get("error"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Parse request body
        body = await request.json()
        phone = body.get("phone", "").strip()
        
        # Validate phone number
        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required"
            )
        
        if len(phone) != 10 or not phone.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number must be exactly 10 digits"
            )
        
        # Get user profile
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update phone number
        user.phone = phone
        db.commit()
        db.refresh(user)
        
        logger.info(f"Phone number updated for user {user_id}")
        
        return {
            "success": True,
            "message": "Phone number updated successfully",
            "phone": phone
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating phone number: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update phone number"
        )


@router.post("/kyc/upload")
async def upload_kyc_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload KYC document
    
    Args:
        request: FastAPI request object
        document_type: Type of document (aadhaar_front, aadhaar_back, dl_front, dl_back)
        file: Uploaded file
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        JSON response with upload status
    """
    from app.services.kyc_service import kyc_service
    from datetime import datetime
    
    try:
        if current_user.get("error"):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Upload document
        file_url = await kyc_service.upload_kyc_document(
            db, user_id, document_type, file
        )
        
        if not file_url:
            raise HTTPException(status_code=400, detail="Failed to upload document")
        
        return JSONResponse({
            "success": True,
            "document_type": document_type,
            "file_url": file_url,
            "uploaded_at": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading KYC document: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload document")

