"""
API routes package.

This package contains all the API route modules for the application.
"""

# Import routers
from .candidates import router as candidates_router
from .upload import router as upload_router
from .automation import router as automation_router
from .admin import router as admin_router

# List of all routers to be included in the FastAPI app
__all__ = [
    'candidates_router',
    'upload_router',
    'automation_router',
    'admin_router'
]
