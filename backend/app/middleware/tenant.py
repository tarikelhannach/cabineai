"""
Tenant Middleware for Multi-Tenant Data Isolation
Ensures all database queries are automatically filtered by firm_id
"""

from fastapi import Request, HTTPException, status
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts firm_id from the authenticated user's JWT token
    and makes it available throughout the request lifecycle for data isolation.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip tenant validation for public routes
        public_routes = [
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/docs",
            "/openapi.json",
            "/health",
            "/billing/init"  # Initial firm registration
        ]
        
        # Check if the current path is public
        if any(request.url.path.startswith(route) for route in public_routes):
            return await call_next(request)
        
        # For protected routes, extract firm_id from the authenticated user
        # This assumes authentication middleware has already run and set request.state.user
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            
            # Extract firm_id from user
            if hasattr(user, "firm_id"):
                request.state.firm_id = user.firm_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not belong to any firm"
                )
        else:
            # If no user is authenticated on a protected route, let auth middleware handle it
            pass
        
        response = await call_next(request)
        return response


def get_current_firm_id(request: Request) -> int:
    """
    Helper function to get the current firm_id from request state.
    Should be used in route dependencies.
    """
    if not hasattr(request.state, "firm_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firm context not found. User may not be authenticated."
        )
    return request.state.firm_id
