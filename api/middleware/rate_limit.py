"""
Rate limiting middleware for API requests.
"""

import time
import json
import hashlib
import logging
from typing import Callable, Awaitable, Tuple, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from functools import wraps
import os

logger = logging.getLogger(__name__)

# Rate limit configuration (requests per window)
DEFAULT_RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # in seconds
RATE_LIMIT_HEADERS = {
    "X-RateLimit-Limit": str(DEFAULT_RATE_LIMIT),
    "X-RateLimit-Remaining": "0",
    "X-RateLimit-Reset": "0",
}

# Redis client (if available)
redis_client = None
if os.getenv("REDIS_URL"):
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL"))
        logger.info("Connected to Redis for rate limiting")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")


def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client making the request.
    
    Args:
        request: The incoming request
        
    Returns:
        str: A string identifying the client
    """
    # Try to get the client's IP address
    client_ip = request.client.host if request.client else "unknown"
    
    # If there's an API key, use that instead of IP
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    
    # Fall back to IP-based identification
    return f"ip:{client_ip}"


def get_rate_limit_key(request: Request) -> str:
    """
    Generate a Redis key for rate limiting.
    
    Args:
        request: The incoming request
        
    Returns:
        str: A Redis key for rate limiting
    """
    client_id = get_client_identifier(request)
    path = request.url.path
    window = int(time.time() // RATE_LIMIT_WINDOW)
    
    # Create a unique key for this client + endpoint + time window
    key = f"rate_limit:{client_id}:{path}:{window}"
    return key


async def rate_limit_middleware(request: Request, call_next) -> Response:
    """
    Middleware to enforce rate limiting.
    
    Args:
        request: The incoming request
        call_next: Function to call the next middleware
        
    Returns:
        Response: The response from the next middleware or a 429 response if rate limited
    """
    # Skip rate limiting for health checks and metrics
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    if not redis_client:
        # If Redis is not available, skip rate limiting
        return await call_next(request)
    
    key = get_rate_limit_key(request)
    
    try:
        # Use Redis INCR to atomically increment the counter
        current = await redis_client.incr(key)
        
        # Set expiration if this is the first request in the window
        if current == 1:
            await redis_client.expire(key, RATE_LIMIT_WINDOW)
        
        # Calculate remaining requests and reset time
        remaining = max(0, DEFAULT_RATE_LIMIT - current)
        reset_time = ((int(time.time()) // RATE_LIMIT_WINDOW) + 1) * RATE_LIMIT_WINDOW
        
        # Add rate limit headers to the response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(DEFAULT_RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        # Check if rate limit is exceeded
        if current > DEFAULT_RATE_LIMIT:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit exceeded: {DEFAULT_RATE_LIMIT} requests per {RATE_LIMIT_WINDOW} seconds"
                }
            )
            response.headers.update({
                "Retry-After": str(RATE_LIMIT_WINDOW),
                "X-RateLimit-Limit": str(DEFAULT_RATE_LIMIT),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
            })
        
        return response
    
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # If there's an error with Redis, allow the request to proceed
        return await call_next(request)


def rate_limited(limit: int = DEFAULT_RATE_LIMIT, window: int = RATE_LIMIT_WINDOW):
    """
    Decorator to apply rate limiting to a specific endpoint.
    
    Args:
        limit: Maximum number of requests allowed in the time window
        window: Time window in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_client:
                return await func(*args, **kwargs)
                
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                return await func(*args, **kwargs)
            
            key = get_rate_limit_key(request)
            key = f"rl_decorator:{key}"
            
            try:
                current = await redis_client.incr(key)
                if current == 1:
                    await redis_client.expire(key, window)
                
                remaining = max(0, limit - current)
                reset_time = int(time.time() // window + 1) * window
                
                if current > limit:
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "Too many requests",
                            "detail": f"Rate limit exceeded: {limit} requests per {window} seconds"
                        }
                    )
                    response.headers.update({
                        "Retry-After": str(window),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                    })
                    return response
                
                # Call the original function
                response = await func(*args, **kwargs)
                
                # Add rate limit headers to the response
                if hasattr(response, 'headers'):
                    response.headers["X-RateLimit-Limit"] = str(limit)
                    response.headers["X-RateLimit-Remaining"] = str(remaining)
                    response.headers["X-RateLimit-Reset"] = str(reset_time)
                
                return response
                
            except Exception as e:
                logger.error(f"Rate limiting decorator error: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

