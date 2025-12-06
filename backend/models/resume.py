"""Resume and WorkExperience models."""

from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, Date, DateTime, Enum as SQLEnum, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from backend.database import Base


class Resume(Base):
    """Resume model for storing uploaded resumes and parsed data."""

    __tablename__ = "resumes"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # File information
    file_name = Column(String(255), nullable=True)
    file_url = Column(String(1024), nullable=True)  # S3 or local path
    file_type = Column(String(50), nullable=True)  # "pdf", "docx", "text"
    file_size = Column(Integer, nullable=True)  # bytes

    # Raw content
    raw_text = Column(Text, nullable=True)

    # Parsed summary
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    github_url = Column(String(512), nullable=True)
    portfolio_url = Column(String(512), nullable=True)

    # Professional summary
    summary = Column(Text, nullable=True)

    # Extracted skills (flattened list)
    skills = Column(JSONB, nullable=False, default=list)  # ["Python", "AWS", "FastAPI"]

    # Education (list of education entries)
    education = Column(JSONB, nullable=False, default=list)  # [{"degree": "BS", "school": "MIT", "year": 2020}]

    # Certifications
    certifications = Column(JSONB, nullable=False, default=list)  # ["AWS Solutions Architect", "PMP"]

    # Languages
    languages = Column(JSONB, nullable=False, default=list)  # ["English", "Spanish"]

    # Parsing metadata
    parsed_at = Column(DateTime(timezone=True), nullable=True)
    parsing_version = Column(String(50), default="v1")
    parse_quality_score = Column(Integer, nullable=True)  # 0-100, how confident we are in the parse

    # AI embedding for resume matching
    resume_embedding = Column(Vector(1536))  # OpenAI ada-002 dimension

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="resume")
    work_experiences = relationship("WorkExperience", back_populates="resume", cascade="all, delete-orphan", order_by="desc(WorkExperience.start_date)")

    @property
    def total_experience_years(self) -> int:
        """Calculate total years of experience from work history."""
        if not self.work_experiences:
            return 0

        total_months = 0
        for exp in self.work_experiences:
            if exp.start_date:
                end = exp.end_date or date.today()
                months = (end.year - exp.start_date.year) * 12 + (end.month - exp.start_date.month)
                total_months += max(0, months)

        return total_months // 12

    @property
    def experience_text(self) -> str:
        """Generate text representation of experience for embeddings."""
        parts = []

        if self.summary:
            parts.append(self.summary)

        if self.skills:
            parts.append(f"Skills: {', '.join(self.skills)}")

        for exp in self.work_experiences or []:
            parts.append(f"{exp.title} at {exp.company}: {exp.description or ''}")
            if exp.achievements:
                parts.append(" ".join(exp.achievements))

        return " ".join(parts)


class WorkExperience(Base):
    """Work experience entries from a resume."""

    __tablename__ = "work_experiences"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    resume_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.resumes.id", ondelete="CASCADE"), nullable=False)

    # Position info
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)

    # Employment type
    employment_type = Column(String(50), nullable=True)  # "full-time", "contract", "freelance", "part-time"
    is_remote = Column(Boolean, default=False)

    # Duration
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)  # NULL = current position
    is_current = Column(Boolean, default=False)

    # Content
    description = Column(Text, nullable=True)
    achievements = Column(JSONB, nullable=False, default=list)  # ["Increased performance by 40%", ...]

    # Skills and technologies used
    skills_used = Column(JSONB, nullable=False, default=list)  # ["Python", "AWS"]

    # Quantified metrics (if extractable)
    metrics = Column(JSONB, nullable=False, default=dict)  # {"revenue_impact": "$2M", "team_size": 5}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="work_experiences")

    @property
    def duration_months(self) -> int:
        """Calculate duration in months."""
        if not self.start_date:
            return 0
        end = self.end_date or date.today()
        return (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)

    @property
    def duration_text(self) -> str:
        """Human-readable duration."""
        months = self.duration_months
        years = months // 12
        remaining_months = months % 12

        if years > 0 and remaining_months > 0:
            return f"{years}y {remaining_months}m"
        elif years > 0:
            return f"{years}y"
        else:
            return f"{remaining_months}m"
