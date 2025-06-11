"""
Analysis API router for CV and job description analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging

# Import AI client
from core.ai.llm_client import analyze_cv, analyze_job_description

# Create the router
router = APIRouter(
    prefix="/analyze",
    tags=["analyze"],
    responses={404: {"description": "Not found"}},
)

# Configure logging
logger = logging.getLogger(__name__)

# Models
class AnalyzeRequest(BaseModel):
    """Request model for analysis endpoints."""
    text: str
    language: str = "en"
    options: Dict[str, Any] = {}

class AnalyzeResponse(BaseModel):
    """Response model for analysis endpoints."""
    status: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {}

# Endpoints
@router.post("/cv", response_model=AnalyzeResponse)
async def analyze_cv_endpoint(request: AnalyzeRequest):
    """
    Analyze a CV/resume.
    
    Args:
        request: Analysis request containing the CV text
        
    Returns:
        Analysis results
    """
    try:
        # Call the AI client to analyze the CV
        analysis_result = await analyze_cv(
            text=request.text,
            language=request.language,
            **request.options
        )
        
        return {
            "status": "success",
            "data": analysis_result,
            "metadata": {
                "language": request.language,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"CV analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CV analysis failed: {str(e)}"
        )

@router.post("/job", response_model=AnalyzeResponse)
async def analyze_job_endpoint(request: AnalyzeRequest):
    """
    Analyze a job description.
    
    Args:
        request: Analysis request containing the job description text
        
    Returns:
        Analysis results
    """
    try:
        # Call the AI client to analyze the job description
        analysis_result = await analyze_job_description(
            text=request.text,
            language=request.language,
            **request.options
        )
        
        return {
            "status": "success",
            "data": analysis_result,
            "metadata": {
                "language": request.language,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Job description analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job description analysis failed: {str(e)}"
        )

# Add imports at the end to avoid circular imports
from pydantic import BaseModel
from datetime import datetime
