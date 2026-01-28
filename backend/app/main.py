"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings

# Create FastAPI application
app = FastAPI(
    title="Lender Matching Platform API",
    description="API for matching loan applications with lenders based on policy criteria",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router with v1 prefix
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "Lender Matching Platform API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }
