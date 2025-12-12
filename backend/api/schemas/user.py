"""User and UserProfile Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    is_active: Optional[bool] = None


class UserRead(UserBase):
    """User read schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_active: bool
    is_premium: bool
    created_at: datetime
    updated_at: datetime


class UserProfileBase(BaseModel):
    """Base user profile schema."""
    profession: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: int = Field(default=0, ge=0, le=50)
    certifications: List[str] = Field(default_factory=list)
    preferences: Dict = Field(default_factory=dict)
    min_rate_usd: Optional[Decimal] = Field(None, ge=0)
    max_hours_per_week: Optional[int] = Field(None, ge=1, le=168)
    availability: Dict = Field(default_factory=dict)
    portfolio: Dict = Field(default_factory=dict)


class UserProfileCreate(UserProfileBase):
    """User profile creation schema."""
    pass


class UserProfileUpdate(BaseModel):
    """User profile update schema."""
    profession: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    certifications: Optional[List[str]] = None
    preferences: Optional[Dict] = None
    min_rate_usd: Optional[Decimal] = Field(None, ge=0)
    max_hours_per_week: Optional[int] = Field(None, ge=1, le=168)
    availability: Optional[Dict] = None
    portfolio: Optional[Dict] = None


class UserProfileRead(UserProfileBase):
    """User profile read schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    avoid_keywords: List[str] = Field(default_factory=list)
    preferred_industries: List[str] = Field(default_factory=list)
    is_remote_only: bool = False


class UserWithProfile(UserRead):
    """User with profile schema."""
    profile: Optional[UserProfileRead] = None