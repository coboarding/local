"""
Admin API router for system management and monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader
from typing import Dict, Any, List, Optional
import logging
import platform
import psutil
import os
import sys
from datetime import datetime, timedelta
from pydantic import BaseModel

# Import settings
from core.config import settings

# Create the router
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)

# Configure logging
logger = logging.getLogger(__name__)


# Security
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_admin_key(api_key_header: str = Security(api_key_header)) -> bool:
    """Verify admin API key."""
    if not api_key_header or api_key_header != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key"
        )
    return True

# Models
class SystemInfo(BaseModel):
    """System information model."""
    platform: str
    python_version: str
    cpu_percent: float
    memory_percent: float
    disk_usage: Dict[str, Any]
    uptime: str
    current_time: datetime

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
    timestamp: datetime
    dependencies: Dict[str, str]

class LogLevelUpdate(BaseModel):
    """Log level update model."""
    logger: str = "root"
    level: str

# Endpoints
@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic information about the service status.
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow(),
        "dependencies": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            # Add other dependencies here
        }
    }

@router.get("/system-info", response_model=SystemInfo)
async def get_system_info(
    _: bool = Depends(verify_admin_key)
):
    """
    Get system information.
    
    Requires admin authentication.
    """
    # Get uptime
    uptime_seconds = psutil.boot_time()
    uptime_str = str(timedelta(seconds=uptime_seconds))
    
    # Get disk usage for the root directory
    disk_usage = psutil.disk_usage('/')
    
    return {
        "platform": platform.platform(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "percent": disk_usage.percent
        },
        "uptime": uptime_str,
        "current_time": datetime.utcnow()
    }

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_logs(
    lines: int = 100,
    level: Optional[str] = None,
    _: bool = Depends(verify_admin_key)
):
    """
    Get application logs.
    
    Args:
        lines: Number of log lines to return (most recent first)
        level: Filter logs by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        List of log entries
    """
    # In a production environment, you would query your logging system here
    # This is a simplified example that returns a fixed response
    return [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Admin endpoint accessed",
            "source": "admin"
        }
    ][:lines]

@router.post("/logs/level", status_code=status.HTTP_200_OK)
async def set_log_level(
    log_level: LogLevelUpdate,
    _: bool = Depends(verify_admin_key)
):
    """
    Set the logging level for a logger.
    
    Args:
        log_level: Log level configuration
    """
    import logging
    
    try:
        level = getattr(logging, log_level.level.upper(), None)
        if not isinstance(level, int):
            raise ValueError(f"Invalid log level: {log_level.level}")
            
        logger = logging.getLogger(log_level.logger)
        logger.setLevel(level)
        
        # Also update handlers if they exist
        for handler in logger.handlers:
            handler.setLevel(level)
            
        return {"status": "success", "logger": log_level.logger, "level": logging.getLevelName(level)}
        
    except Exception as e:
        logger.error(f"Failed to set log level: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to set log level: {str(e)}"
        )

@router.post("/cache/clear", status_code=status.HTTP_200_OK)
async def clear_cache(
    cache_key: Optional[str] = None,
    _: bool = Depends(verify_admin_key)
):
    """
    Clear application cache.
    
    Args:
        cache_key: Optional specific cache key to clear. If not provided, clears all caches.
    """
    # In a production environment, you would clear your cache here
    # This is a simplified example
    return {
        "status": "success",
        "message": f"Cache cleared{f' for key: {cache_key}' if cache_key else ''}",
        "timestamp": datetime.utcnow()
    }

@router.get("/config", response_model=Dict[str, Any])
async def get_config(
    _: bool = Depends(verify_admin_key)
):
    """
    Get current application configuration.
    
    Note: Sensitive values will be redacted.
    """
    # Create a safe copy of settings, redacting sensitive values
    config = {}
    for key, value in settings.dict().items():
        # Redact sensitive keys
        if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
            config[key] = "***REDACTED***"
        else:
            config[key] = value
            
    return config

@router.get("/tasks", response_model=List[Dict[str, Any]])
async def list_background_tasks(
    _: bool = Depends(verify_admin_key)
):
    """
    List background tasks.
    
    Returns information about currently running background tasks.
    """
    # In a production environment, you would query your task queue here
    # This is a simplified example
    return []
