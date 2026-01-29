"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, applications, underwriting, lenders, policies

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    tags=["health"],
)

api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["applications"],
)

api_router.include_router(
    underwriting.router,
    prefix="/underwriting",
    tags=["underwriting"],
)

api_router.include_router(
    lenders.router,
    prefix="/lenders",
    tags=["lenders"],
)

api_router.include_router(
    policies.router,
    prefix="/policies",
    tags=["policies"],
)
