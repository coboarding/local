"""
Main FastAPI application module for the coBoarding API.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import os

# Import routers
from .routes import candidates, upload, automation, admin
from .middleware.auth import verify_api_key
from .middleware.rate_limit import rate_limit_middleware
from .middleware.compliance import compliance_middleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="coBoarding API",
    description="AI-powered job application automation API",
    version="0.1.0",
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(compliance_middleware)

# Include routers
app.include_router(
    candidates.router,
    prefix="/api/candidates",
    tags=["candidates"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    upload.router,
    prefix="/api/upload",
    tags=["upload"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    automation.router,
    prefix="/api/automation",
    tags=["automation"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    admin.router,
    prefix="/api/admin",
    tags=["admin"],
)

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

# Root endpoint
@app.get("/", tags=["root"])
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "coBoarding API",
        "version": "0.1.0",
        "docs": "/docs",
    }

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# This allows running the app directly with: python -m api.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
