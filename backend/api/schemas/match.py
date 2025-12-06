"""JobMatch Pydantic schemas."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from backend.api.schemas.job import JobRead


class JobMatchBase(BaseModel):
    """Base job match schema."""
    score: Decimal = Field(..., ge=0, le=100)
    score_breakdown: Dict = Field(default_factory=dict)
    explanation: Optional[str] = None
    status: str = Field(default="new", pattern="^(new|viewed|saved|applied|rejected|interviewed|hired)$")
    proposal: Optional[str] = None


class JobMatchCreate(JobMatchBase):
    """Job match creation schema."""
    job_id: UUID


class JobMatchUpdate(BaseModel):
    """Job match update schema."""
    status: Optional[str] = Field(None, pattern="^(viewed|saved|applied|rejected|interviewed|hired)$")
    proposal: Optional[str] = None


class JobMatchRead(JobMatchBase):
    """Job match read schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    job_id: UUID
    applied_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    semantic_score: float
    keyword_score: float
    compensation_score: float
    ml_score: float
    is_high_match: bool
    days_since_created: int
    
    # Related job data
    job: Optional[JobRead] = None