"""
Authentication middleware for validating local JWT tokens (Web Only)
"""

from typing import List, Callable
from fastapi import Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging_config import logger
from app.core.security import decode_access_token


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate local JWT access tokens for WEB routes only.
    API routes (/api/*) are completely ignored.
    """

    EXEMPTED_URLS: List[str] = [
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
        "/cars",
        "/payment",
        "/booking",
        "/contact",


    EXEMPTED_PREFIXES: List[str] = [
        "/static",
        "/auth",
        "/admin",
        "/cars",
        "/payments/callback",
        "/payments/cancel",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:

        path = request.url.path

        # 🔥 1️⃣ VERY IMPORTANT: Skip ALL API routes
        # This prevents HTML redirects for mobile/API requests
        if path.startswith("/api"):
            return await call_next(request)

        # 2️⃣ Skip exempted URLs
        if self._is_exempted(path):
            return await call_next(request)

        # 3️⃣ Web session authentication (cookie-based)
        access_token = request.cookies.get("access_token")

        if not access_token:
            logger.debug(f"No access token for {path}")
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

        # 4️⃣ Validate token
        if not self._validate_token(access_token):
            logger.warning(f"Invalid token for {path}")
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.delete_cookie("access_token")
            response.delete_cookie("username")
            return response

        return await call_next(request)

    def _is_exempted(self, path: str) -> bool:
        if path in self.EXEMPTED_URLS:
            return True

        for prefix in self.EXEMPTED_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    def _validate_token(self, token: str) -> bool:
        try:
            decoded = decode_access_token(token)
            return decoded is not None
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False
