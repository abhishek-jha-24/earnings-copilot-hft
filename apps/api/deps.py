"""
FastAPI dependencies for the earnings copilot API.
Provides database connections and common dependencies.
"""

from typing import AsyncGenerator
from services.storage import db_manager
from apps.api.auth import get_current_user_role, get_current_user_id


async def get_db():
    """Get database connection dependency."""
    async with db_manager.get_connection() as conn:
        yield conn


# Re-export auth dependencies for convenience
get_role = get_current_user_role
get_user_id = get_current_user_id
