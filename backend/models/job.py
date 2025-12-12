"""Job and JobMatch models."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, DECIMAL, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# pgvector import - commented out for local dev without pgvector extension
# from pgvector.sqlalchemy import Vector

from backend.database import Base


class Job(Base):
    """Job posting model with embeddings for AI matching."""
    
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_job_source_id"),
        {"schema": "jobseeker"}
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Source information
    source = Column(String(50), nullable=False, index=True)  # "upwork", "linkedin", "indeed"
    source_id = Column(String(255))  # Original job ID from source platform
    url = Column(Text)  # Direct link to job posting
    
    # Basic job details
    title = Column(Text, nullable=False)
    company = Column(String(255), index=True)
    description = Column(Text)
    
    # Job requirements and skills
    requirements = Column(JSONB, nullable=False, default=list)  # ["Python", "AWS", "3+ years"]
    skills = Column(JSONB, nullable=False, default=list)  # ["python", "aws", "lambda"]
    
    # Compensation
    rate_min = Column(DECIMAL(10, 2))
    rate_max = Column(DECIMAL(10, 2))
    rate_type = Column(String(20))  # "hourly", "fixed", "annual"
    
    # Work arrangement
    location = Column(String(255))
    remote = Column(Boolean, default=False, index=True)
    hours_per_week = Column(Integer)
    duration = Column(String(100))  # "3 months", "ongoing", "1 week"
    
    # Timing
    posted_at = Column(DateTime(timezone=True), index=True)
    expires_at = Column(DateTime(timezone=True))
    
    # Raw data from source
    raw_data = Column(JSONB, nullable=False, default=dict)
    
    # AI embedding for job matching - commented out for local dev without pgvector
    # job_embedding = Column(Vector(1536))  # OpenAI ada-002 dimension
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    
    @property
    def rate_range_text(self) -> str:
        """Get formatted rate range."""
        if not self.rate_min and not self.rate_max:
            return "Rate not specified"
        
        rate_type = self.rate_type or "unknown"
        
        if self.rate_min and self.rate_max:
            if self.rate_min == self.rate_max:
                return f"${self.rate_min}/{rate_type}"
            return f"${self.rate_min}-${self.rate_max}/{rate_type}"
        elif self.rate_min:
            return f"${self.rate_min}+/{rate_type}"
        elif self.rate_max:
            return f"Up to ${self.rate_max}/{rate_type}"
        
        return "Rate not specified"
    
    @property
    def job_embeddings_text(self) -> str:
        """Generate text representation for embeddings."""
        parts = [
            self.title,
            self.company or "",
            self.description or "",
            " ".join(self.skills),
            " ".join(self.requirements),
            self.location or "",
            "remote" if self.remote else "",
        ]
        
        return " ".join(filter(None, parts))
    
    @property
    def is_active(self) -> bool:
        """Check if job posting is still active."""
        if self.expires_at:
            return datetime.utcnow() < self.expires_at.replace(tzinfo=None)
        return True


class JobMatch(Base):
    """Job match with user scoring and status tracking."""
    
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_match"),
        {"schema": "jobseeker"}
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.jobs.id", ondelete="CASCADE"), nullable=False)
    
    # Scoring information
    score = Column(DECIMAL(5, 2), nullable=False, index=True)  # 0-100 score
    score_breakdown = Column(JSONB, nullable=False, default=dict)  # {"semantic": 85, "keywords": 90}
    explanation = Column(Text)  # Human-readable explanation of the match
    
    # Match status and user actions
    status = Column(String(50), default="new", nullable=False, index=True)
    # Status values: "new", "viewed", "saved", "applied", "rejected", "interviewed", "hired"
    
    # Proposal and application tracking
    proposal = Column(Text)  # Generated or custom proposal
    client_notes = Column(Text)  # User's personal notes about the match
    applied_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="job_matches")
    job = relationship("Job", back_populates="matches")
    feedback = relationship("UserFeedback", back_populates="match", cascade="all, delete-orphan")
    
    @property
    def semantic_score(self) -> float:
        """Get semantic similarity score component."""
        return self.score_breakdown.get("semantic", 0.0)
    
    @property
    def keyword_score(self) -> float:
        """Get keyword matching score component."""
        return self.score_breakdown.get("keywords", 0.0)
    
    @property
    def compensation_score(self) -> float:
        """Get compensation fit score component."""
        return self.score_breakdown.get("compensation", 0.0)
    
    @property
    def ml_score(self) -> float:
        """Get ML prediction score component."""
        return self.score_breakdown.get("ml_prediction", 0.0)
    
    @property
    def is_high_match(self) -> bool:
        """Check if this is a high-quality match."""
        return self.score >= 80.0
    
    @property
    def days_since_created(self) -> int:
        """Get number of days since match was created."""
        delta = datetime.utcnow() - self.created_at.replace(tzinfo=None)
        return delta.days