"""
Authentication Middleware
Sets request.state.user from JWT token for use by other middlewares (TenantMiddleware, RateLimiter, etc.)
"""

from fastapi import Request, HTTPException, status
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from ..auth.jwt import decode_token
from ..database import get_db
from ..models import User

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts and validates JWT token, then sets request.state.user
    for use by TenantMiddleware, RateLimiter, and other components.
    """
    
    # Public routes that don't require authentication
    PUBLIC_ROUTES = [
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/password/reset-request",
        "/api/auth/password/reset-confirm",
        "/billing/init",  # Initial firm registration
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for public routes
        if any(request.url.path.startswith(route) for route in self.PUBLIC_ROUTES):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            # For protected routes without token, let the route handler return 401
            # (Don't set request.state.user, so TenantMiddleware will handle it)
            return await call_next(request)
        
        token = authorization.split(" ")[1]
        
        # Decode and validate token
        payload = decode_token(token)
        if not payload:
            # Invalid token - let route handler return 401
            return await call_next(request)
        
        # Get user from database
        email = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not email:
            return await call_next(request)
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
            else:
                user = db.query(User).filter(User.email == email).first()
            
            if user and user.is_active:
                # Set user in request state for use by other middlewares
                request.state.user = user
                logger.debug(f"Authenticated user: {user.email} (firm_id: {user.firm_id})")
            else:
                logger.warning(f"User not found or inactive: {email}")
        except Exception as e:
            logger.error(f"Error loading user in auth middleware: {e}")
        finally:
            db.close()
        
        return await call_next(request)

