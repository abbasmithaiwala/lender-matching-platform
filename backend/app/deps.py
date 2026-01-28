"""Dependency injection for FastAPI endpoints."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

__all__ = ["get_db"]


# Re-export get_db for convenience
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.

    This is an alias for get_db for clarity in endpoint signatures.
    """
    async for session in get_db():
        yield session
