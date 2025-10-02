"""
Authentication middleware and utilities for the earnings copilot API.
Handles API key authentication with role-based access control.
"""

import os
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader


# API key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Load API keys from environment
ADMIN_API_KEY = os.getenv("API_KEY_ADMIN", "admin-secret")
TRADER_API_KEY = os.getenv("API_KEY_TRADER", "trader-secret")


class Role:
    """User roles."""
    ADMIN = "ADMIN"
    TRADER = "TRADER"


def get_role_from_api_key(api_key: str) -> Optional[str]:
    """Map API key to role."""
    if api_key == ADMIN_API_KEY:
        return Role.ADMIN
    elif api_key == TRADER_API_KEY:
        return Role.TRADER
    return None


async def get_current_user_role(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    Extract and validate API key from request headers.
    Returns the user role or raises HTTPException.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    role = get_role_from_api_key(api_key)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return role


async def require_admin_role(role: str = Depends(get_current_user_role)) -> str:
    """Require admin role for protected endpoints."""
    if role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return role


async def require_trader_role(role: str = Depends(get_current_user_role)) -> str:
    """Require trader or admin role for trading endpoints."""
    if role not in [Role.ADMIN, Role.TRADER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trader access required"
        )
    return role


def get_user_id_from_api_key(api_key: str) -> Optional[str]:
    """Get user ID from API key for subscription management."""
    role = get_role_from_api_key(api_key)
    if role == Role.ADMIN:
        return "admin_user"
    elif role == Role.TRADER:
        return "trader_user"
    return None


async def get_current_user_id(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """Get current user ID from API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    user_id = get_user_id_from_api_key(api_key)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return user_id
