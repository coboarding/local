"""
Authentication middleware for API key validation.
"""

from fastapi import HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader
from typing import Optional, Dict, Any
import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# API Key Header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Get valid API keys from environment
API_KEYS = set(
    key.strip()
    for key in os.getenv("API_KEYS", "").split(",")
    if key.strip()
)

# Add a default API key if none are provided in the environment
if not API_KEYS:
    DEFAULT_API_KEY = "test-api-key-123"  # This should be overridden in production
    API_KEYS.add(DEFAULT_API_KEY)
    logger.warning("Using default API key. This should only be used for development.")


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the request header.
    
    Args:
        api_key: The API key from the request header
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If the API key is invalid or missing
    """
    if not api_key:
        logger.warning("API key is missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "API key is missing"},
        )
    
    if api_key not in API_KEYS:
        logger.warning(f"Invalid API key attempt: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Invalid API key"},
        )
    
    return api_key


def api_key_required(func):
    """
    Decorator to require API key authentication for a route.
    
    Example:
        @app.get("/protected")
        @api_key_required
        async def protected_route():
            return {"message": "This is a protected route"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "Request object not found"},
            )
        
        api_key = request.headers.get(API_KEY_NAME)
        verify_api_key(api_key)
        return await func(*args, **kwargs)
    
    return wrapper


# For backwards compatibility
# This allows using either the dependency injection or the decorator
api_key_auth = api_key_required
