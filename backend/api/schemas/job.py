"""Job Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class JobBase(BaseModel):
    """Base job schema."""
    title: str = Field(..., min_length=1, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    requirements: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    rate_min: Optional[Decimal] = Field(None, ge=0)
    rate_max: Optional[Decimal] = Field(None, ge=0)
    rate_type: Optional[str] = Field(None, pattern="^(hourly|fixed|annual)$")
    location: Optional[str] = Field(None, max_length=255)
    remote: bool = False
    hours_per_week: Optional[int] = Field(None, ge=1, le=168)
    duration: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = None


class JobCreate(JobBase):
    """Job creation schema."""
    source: str = Field(..., min_length=1, max_length=50)
    source_id: Optional[str] = Field(None, max_length=255)
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    raw_data: Dict = Field(default_factory=dict)


class JobUpdate(BaseModel):
    """Job update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    company: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    rate_min: Optional[Decimal] = Field(None, ge=0)
    rate_max: Optional[Decimal] = Field(None, ge=0)
    rate_type: Optional[str] = Field(None, pattern="^(hourly|fixed|annual)$")
    location: Optional[str] = Field(None, max_length=255)
    remote: Optional[bool] = None
    hours_per_week: Optional[int] = Field(None, ge=1, le=168)
    duration: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = None
    expires_at: Optional[datetime] = None


class JobRead(JobBase):
    """Job read schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    source: str
    source_id: Optional[str]
    posted_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    rate_range_text: str
    is_active: bool


class JobSummary(BaseModel):
    """Job summary schema for lists."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    title: str
    company: Optional[str]
    location: Optional[str]
    remote: bool
    rate_range_text: str
    skills: List[str]
    posted_at: Optional[datetime]
    is_active: bool


class JobSearch(BaseModel):
    """Job search parameters."""
    query: Optional[str] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    remote_only: Optional[bool] = None
    min_rate: Optional[Decimal] = None
    max_rate: Optional[Decimal] = None
    rate_type: Optional[str] = None
    sources: Optional[List[str]] = None
    posted_after: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)