"""
Compliance and security middleware for the API.
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import re
import os
from functools import wraps

logger = logging.getLogger(__name__)

# Security headers configuration
DEFAULT_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self';",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site"
}

# Sensitive data patterns to redact in logs
SENSITIVE_PATTERNS = [
    (r'"password"\s*:\s*"[^"]*"', '"password": "[REDACTED]"'),
    (r'"api[_-]?key"\s*:\s*"[^"]*"', '"api_key": "[REDACTED]"'),
    (r'"token"\s*:\s*"[^"]*"', '"token": "[REDACTED]"'),
    (r'"secret"\s*:\s*"[^"]*"', '"secret": "[REDACTED]"'),
    (r'"authorization"\s*:\s*"[^"]*"', '"authorization": "[REDACTED]"'),
]

# Paths that should not be logged
EXCLUDED_PATHS = [
    "/health",
    "/metrics",
    "/favicon.ico"
]

# Rate limiting for compliance events
COMPLIANCE_EVENT_LIMIT = 100  # Max events per minute
compliance_events = []


def redact_sensitive_data(data: str) -> str:
    """
    Redact sensitive information from logs.
    
    Args:
        data: The data to redact
        
    Returns:
        str: The redacted data
    """
    if not data:
        return data
    
    try:
        # Try to parse as JSON first
        json_data = json.loads(data)
        redacted = _redact_json(json_data)
        return json.dumps(redacted)
    except (json.JSONDecodeError, TypeError):
        # If not JSON, treat as plain text
        text = str(data)
        for pattern, replacement in SENSITIVE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text


def _redact_json(data: Any) -> Any:
    """Recursively redact sensitive data from JSON objects."""
    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if any(s in k.lower() for s in ["password", "secret", "token", "key", "auth"])
            else _redact_json(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [_redact_json(item) for item in data]
    return data


async def compliance_middleware(request: Request, call_next) -> Response:
    """
    Middleware to handle compliance and security headers.
    
    Args:
        request: The incoming request
        call_next: Function to call the next middleware
        
    Returns:
        Response: The response with security headers
    """
    # Skip middleware for excluded paths
    if any(request.url.path.startswith(path) for path in EXCLUDED_PATHS):
        return await call_next(request)
    
    # Log request
    request_id = request.headers.get("X-Request-ID", "")
    client_ip = request.client.host if request.client else "unknown"
    
    # Log request details (redacted)
    request_body = ""
    try:
        request_body = await request.body()
        request_body = redact_sensitive_data(request_body.decode())
    except Exception as e:
        logger.warning(f"Failed to read request body: {e}")
    
    logger.info(
        f"Request: {request.method} {request.url} - Client: {client_ip} - "
        f"Headers: {redact_sensitive_data(str(dict(request.headers)))} - "
        f"Body: {request_body}",
        extra={"request_id": request_id, "client_ip": client_ip}
    )
    
    # Process request
    start_time = time.time()
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(
            f"Request error: {str(e)}",
            exc_info=True,
            extra={"request_id": request_id, "client_ip": client_ip}
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )
    
    # Calculate request duration
    process_time = time.time() - start_time
    
    # Add security headers
    for header, value in DEFAULT_SECURITY_HEADERS.items():
        response.headers[header] = value
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    # Log response
    response_body = ""
    try:
        response_body = redact_sensitive_data(response.body.decode())
    except Exception as e:
        logger.warning(f"Failed to read response body: {e}")
    
    logger.info(
        f"Response: {request.method} {request.url} - Status: {response.status_code} - "
        f"Duration: {process_time:.4f}s - Headers: {dict(response.headers)} - "
        f"Body: {response_body}",
        extra={"request_id": request_id, "client_ip": client_ip, "duration": process_time}
    )
    
    return response


def validate_content_type(content_type: str = "application/json"):
    """
    Decorator to validate request content type.
    
    Args:
        content_type: Expected content type
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                return await func(*args, **kwargs)
            
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type_header = request.headers.get("Content-Type", "")
                if content_type not in content_type_header:
                    return JSONResponse(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        content={"error": f"Unsupported media type. Expected: {content_type}"},
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def log_compliance_event(event_type: str, details: Dict[str, Any]):
    """
    Log a compliance-related event.
    
    Args:
        event_type: Type of compliance event
        details: Event details
    """
    global compliance_events
    
    # Remove events older than 1 minute
    current_time = time.time()
    compliance_events = [
        event for event in compliance_events
        if current_time - event["timestamp"] < 60
    ]
    
    # Check rate limit
    if len(compliance_events) >= COMPLIANCE_EVENT_LIMIT:
        logger.warning("Compliance event rate limit exceeded")
        return
    
    # Add new event
    event = {
        "timestamp": current_time,
        "type": event_type,
        "details": details
    }
    
    compliance_events.append(event)
    logger.info(f"Compliance event: {event_type}", extra={"event": event})
