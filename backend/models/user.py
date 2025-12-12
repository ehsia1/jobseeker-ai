"""User and UserProfile models."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# pgvector import - commented out for local dev without pgvector extension
# from pgvector.sqlalchemy import Vector

from backend.database import Base


class User(Base):
    """User model for authentication and basic info."""
    
    __tablename__ = "users"
    __table_args__ = {"schema": "jobseeker"}
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resume = relationship("Resume", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    job_matches = relationship("JobMatch", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    """User profile with skills, preferences, and job criteria."""
    
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "jobseeker"}
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Professional info
    profession = Column(String, nullable=True)  # "software_engineer", "designer", "marketing", etc.
    job_title = Column(String, nullable=True)  # Current or desired job title
    
    # Skills and experience
    skills = Column(JSONB, nullable=False, default=list)  # ["python", "aws", "lambda"]
    experience_years = Column(Integer, default=0)
    certifications = Column(JSONB, nullable=False, default=list)  # ["AWS Solutions Architect"]
    
    # Job preferences
    preferences = Column(JSONB, nullable=False, default=dict)  # {"remote_only": true, "industries": [...]}
    min_rate_usd = Column(DECIMAL(10, 2))
    max_hours_per_week = Column(Integer)
    availability = Column(JSONB, nullable=False, default=dict)  # {"time_zones": ["PST", "EST"]}
    
    # Portfolio and assets
    portfolio = Column(JSONB, nullable=False, default=dict)  # {"github": "...", "website": "..."}
    
    # AI embedding for profile matching - commented out for local dev
    # profile_embedding = Column(Vector(1536))  # OpenAI ada-002 dimension
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    @property
    def avoid_keywords(self) -> List[str]:
        """Get list of keywords to avoid."""
        return self.preferences.get("avoid_keywords", [])
    
    @property
    def preferred_industries(self) -> List[str]:
        """Get list of preferred industries."""
        return self.preferences.get("industries", [])
    
    @property
    def is_remote_only(self) -> bool:
        """Check if user only wants remote work."""
        return self.preferences.get("remote_only", False)
    
    @property
    def skill_embeddings_text(self) -> str:
        """Generate text representation for embeddings."""
        skills_text = " ".join(self.skills)
        industries_text = " ".join(self.preferred_industries)
        experience_text = f"{self.experience_years} years experience"
        
        return f"{skills_text} {industries_text} {experience_text}"