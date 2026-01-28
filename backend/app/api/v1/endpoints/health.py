"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Health check endpoint.

    Verifies that the API is running and the database is accessible.

    Returns:
        dict: Health status with API and database status
    """
    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "api": "healthy",
        "database": db_status,
    }
