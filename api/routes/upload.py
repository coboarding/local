"""
Upload API router for handling file uploads and processing.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

# Create the router
router = APIRouter(
    prefix="/upload",
    tags=["upload"],
    responses={404: {"description": "Not found"}},
)

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
UPLOAD_DIR.mkdir(exist_ok=True)

# Models
class UploadResponse(BaseModel):
    """Response model for file uploads."""
    filename: str
    content_type: str
    size: int
    saved_path: str
    metadata: Dict[str, Any] = {}

# Helper functions
def allowed_file(filename: str) -> bool:
    """Check if the file has an allowed extension."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

# Endpoints
@router.post("/cv", response_model=UploadResponse)
async def upload_cv(
    file: UploadFile = File(..., description="CV/Resume file to upload"),
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Upload a CV/Resume file for processing.
    
    Supported formats: PDF, DOCX, DOC, TXT
    Max size: 10MB
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
            
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content to get size
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {MAX_FILE_SIZE/1024/1024}MB"
            )
        
        # Create unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.filename).suffix
        filename = f"cv_{timestamp}{file_ext}"
        file_path = UPLOAD_DIR / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Prepare response
        response_data = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file_size,
            "saved_path": str(file_path),
            "metadata": metadata or {}
        }
        
        logger.info(f"Successfully uploaded CV: {filename} ({file_size} bytes)")
        
        # Here you would typically process the CV using the AI service
        # For example: await process_cv(file_path, metadata)
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing file"
        )

@router.post("/bulk", response_model=List[UploadResponse])
async def upload_bulk(
    files: List[UploadFile] = File(..., description="Multiple files to upload")
):
    """
    Upload multiple files at once.
    
    Returns a list of upload results.
    """
    results = []
    
    for file in files:
        try:
            # Reuse the single file upload logic
            result = await upload_cv(file=file)
            results.append(result)
        except HTTPException as e:
            results.append({
                "filename": file.filename,
                "error": e.detail,
                "status": "error"
            })
    
    return results

@router.get("/files", response_model=List[Dict[str, Any]])
async def list_uploads():
    """List all uploaded files."""
    files = []
    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return files

@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(filename: str):
    """Delete an uploaded file."""
    try:
        file_path = UPLOAD_DIR / filename
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_path.unlink()
        logger.info(f"Deleted file: {filename}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting file"
        )

# Add BaseModel import at the end to avoid circular imports
from pydantic import BaseModel
from typing import Optional
