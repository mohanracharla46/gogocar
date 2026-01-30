"""
Authentication middleware for validating Cognito JWT tokens
"""
from typing import List, Callable
from fastapi import Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import cognitojwt
import time

from app.core.config import settings
from app.core.logging_config import logger


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate Cognito JWT access tokens
    Exempts certain URLs from authentication
    """
    
    # Exempted URLs that don't require authentication
    EXEMPTED_URLS: List[str] = [
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/token",
        "/auth/logout",
        "/health",
        "/cars",
        "/payment",
        "/booking",
        "/contact",  # Contact page is public
        "/admin/login",  # Admin login page
    ]
    
    # Exempted URL prefixes (for static files, etc.)
    EXEMPTED_PREFIXES: List[str] = [
        "/static",
        "/auth",
        "/payments/callback",  # CCAvenue callback doesn't have user context
        "/payments/cancel",    # CCAvenue cancel doesn't have user context
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and validate access token
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler
            
        Returns:
            Response object
        """
        # Check if URL is exempted
        if self._is_exempted(request.url.path):
            return await call_next(request)
        
        # Get access_token from cookies
        access_token = request.cookies.get('access_token')
        
        # If no token, redirect to home
        if not access_token:
            logger.debug(f"Access token not found for {request.url.path}")
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
        # Validate token
        is_valid = self._validate_token(access_token)
        
        if not is_valid:
            logger.warning(f"Invalid or expired token for {request.url.path}")
            # Redirect to home (which will show login button)
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            # Clear invalid cookie
            response.delete_cookie(key="access_token")
            response.delete_cookie(key="username")
            return response
        
        # Token is valid, proceed with request
        return await call_next(request)
    
    def _is_exempted(self, path: str) -> bool:
        """
        Check if URL path is exempted from authentication
        
        Args:
            path: URL path to check
            
        Returns:
            True if exempted, False otherwise
        """
        # Exact match
        if path in self.EXEMPTED_URLS:
            return True
        
        # Prefix match (check prefixes first as they can match exact paths)
        for prefix in self.EXEMPTED_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _validate_token(self, token: str) -> bool:
        """
        Validate Cognito JWT token and check expiration
        
        Args:
            token: Access token string
            
        Returns:
            True if valid and not expired, False otherwise
        """
        try:
            # Check if required settings are configured
            if not settings.USERPOOL_ID or not settings.APP_CLIENT_ID:
                logger.warning("Cognito settings not configured, skipping token validation")
                # If Cognito is not configured, allow the request to proceed
                # This is useful for development or when using alternative auth
                return True
            # Basic token format check
            if not token or not isinstance(token, str) or len(token.split('.')) != 3:
                logger.warning("Invalid token format")
                return False
            
            # Decode and validate token using cognitojwt
            decoded_token = cognitojwt.decode(
                token,
                "us-east-1",
                settings.USERPOOL_ID,
                settings.APP_CLIENT_ID
            )
            
            # Check if decoded_token is None or empty
            if not decoded_token:
                logger.warning("Token decoded to None or empty")
                return False
            
            # Check expiration
            exp = decoded_token.get('exp')
            if exp:
                # Get current time in seconds since epoch
                current_time = int(time.time())
                
                # Check if token is expired
                if exp < current_time:
                    logger.warning(f"Token expired. Exp: {exp}, Current: {current_time}")
                    return False
            
            # Token is valid and not expired
            return True
            
        except cognitojwt.CognitoJWTException as e:
            logger.error(f"Cognito JWT exception: {str(e)}")
            return False
        except (TypeError, AttributeError, ValueError) as e:
            logger.error(f"Error validating token (type error): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}", exc_info=True)
            return False

