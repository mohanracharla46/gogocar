"""
Authentication middleware for validating Cognito JWT tokens
"""
from typing import List, Callable
from fastapi import Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging_config import logger
from app.core.security import decode_access_token


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate local JWT access tokens
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
        "/cars",   # Car listing
        "/cars/",  # Car details prefix
        "/payment",
        "/booking",
        "/contact",
        "/admin/login",
    ]
    
    # Exempted URL prefixes
    EXEMPTED_PREFIXES: List[str] = [
        "/static",
        "/auth",
        "/admin",
        "/cars",  # All car routes
        "/payments/callback",
        "/payments/cancel",
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
        Validate local JWT token and check expiration
        
        Args:
            token: Access token string
            
        Returns:
            True if valid and not expired, False otherwise
        """
        try:
            decoded_token = decode_access_token(token)
            return decoded_token is not None
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return False

