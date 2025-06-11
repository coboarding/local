"""
Candidates API router for managing candidate data and operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Create the router
router = APIRouter(
    prefix="/candidates",
    tags=["candidates"],
    responses={404: {"description": "Not found"}},
)

# Temporary in-memory storage for demo purposes
candidates_db = {}

# Models
class CandidateBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    status: str = "new"
    notes: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class Candidate(CandidateBase):
    id: str
    created_at: datetime
    updated_at: datetime

# Endpoints
@router.get("/", response_model=List[Candidate])
async def list_candidates():
    """List all candidates."""
    return list(candidates_db.values())

@router.post("/", response_model=Candidate, status_code=status.HTTP_201_CREATED)
async def create_candidate(candidate: CandidateCreate):
    """Create a new candidate."""
    import uuid
    from datetime import datetime
    
    candidate_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    db_candidate = Candidate(
        **candidate.dict(),
        id=candidate_id,
        created_at=now,
        updated_at=now
    )
    
    candidates_db[candidate_id] = db_candidate
    return db_candidate

@router.get("/{candidate_id}", response_model=Candidate)
async def get_candidate(candidate_id: str):
    """Get a specific candidate by ID."""
    if candidate_id not in candidates_db:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidates_db[candidate_id]

@router.put("/{candidate_id}", response_model=Candidate)
async def update_candidate(candidate_id: str, candidate: CandidateCreate):
    """Update a candidate."""
    if candidate_id not in candidates_db:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    updated_candidate = Candidate(
        **candidate.dict(),
        id=candidate_id,
        created_at=candidates_db[candidate_id].created_at,
        updated_at=datetime.utcnow()
    )
    
    candidates_db[candidate_id] = updated_candidate
    return updated_candidate

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(candidate_id: str):
    """Delete a candidate."""
    if candidate_id not in candidates_db:
        raise HTTPException(status_code=404, detail="Candidate not found")
    del candidates_db[candidate_id]
    return None
