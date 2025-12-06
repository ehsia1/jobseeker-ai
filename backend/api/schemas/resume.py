"""Pydantic schemas for Resume API endpoints."""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class WorkExperienceBase(BaseModel):
    """Base work experience data."""

    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    location: Optional[str] = Field(None, description="Work location")
    employment_type: Optional[str] = Field(
        None, description="Employment type (full-time, contract, freelance, part-time)"
    )
    is_remote: bool = Field(False, description="Whether the position is remote")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date (null if current)")
    is_current: bool = Field(False, description="Whether this is the current position")
    description: Optional[str] = Field(None, description="Role description")
    achievements: List[str] = Field(
        default_factory=list, description="List of achievements/bullet points"
    )
    skills_used: List[str] = Field(
        default_factory=list, description="Skills/technologies used"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Quantified metrics"
    )


class WorkExperienceResponse(WorkExperienceBase):
    """Work experience response with ID."""

    id: UUID
    duration_months: int = Field(..., description="Duration in months")
    duration_text: str = Field(..., description="Human-readable duration")

    class Config:
        from_attributes = True


class EducationEntry(BaseModel):
    """Education entry data."""

    degree: Optional[str] = Field(None, description="Degree name")
    field: Optional[str] = Field(None, description="Field of study")
    school: Optional[str] = Field(None, description="Institution name")
    year: Optional[str] = Field(None, description="Graduation year")
    gpa: Optional[str] = Field(None, description="GPA if mentioned")


class ResumeBase(BaseModel):
    """Base resume data."""

    full_name: Optional[str] = Field(None, description="Full name from resume")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Location (city, state/country)")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[str] = Field(None, description="Portfolio website URL")
    summary: Optional[str] = Field(None, description="Professional summary")
    skills: List[str] = Field(default_factory=list, description="List of skills")
    education: List[EducationEntry] = Field(
        default_factory=list, description="Education entries"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Certifications"
    )
    languages: List[str] = Field(
        default_factory=list, description="Spoken languages"
    )


class ResumeResponse(ResumeBase):
    """Resume response with all fields."""

    id: UUID
    user_id: UUID
    file_name: Optional[str] = Field(None, description="Uploaded file name")
    file_type: Optional[str] = Field(None, description="File type (pdf, docx, text)")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    parsed_at: Optional[datetime] = Field(None, description="When the resume was parsed")
    parse_quality_score: Optional[int] = Field(
        None, description="Parse quality score (0-100)"
    )
    total_experience_years: int = Field(
        ..., description="Total years of work experience"
    )
    work_experiences: List[WorkExperienceResponse] = Field(
        default_factory=list, description="Work experience entries"
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeTextRequest(BaseModel):
    """Request to parse resume from pasted text."""

    text: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="Resume text content (min 50 characters)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "text": """John Doe
Software Engineer
john@example.com | (555) 123-4567

EXPERIENCE
Senior Software Engineer at TechCorp (2020 - Present)
- Built scalable APIs serving 1M+ requests/day
- Led team of 5 engineers
- Technologies: Python, FastAPI, PostgreSQL, AWS

Software Engineer at StartupInc (2018 - 2020)
- Developed microservices architecture
- Improved system performance by 40%

SKILLS
Python, JavaScript, React, AWS, Docker, PostgreSQL
"""
                }
            ]
        }


class ResumeUploadResponse(BaseModel):
    """Response after resume upload/parsing."""

    message: str = Field(..., description="Status message")
    resume: ResumeResponse = Field(..., description="Parsed resume data")


class ResumeSummary(BaseModel):
    """Brief resume summary for listings."""

    id: UUID
    full_name: Optional[str]
    file_name: Optional[str]
    file_type: Optional[str]
    skills_count: int = Field(..., description="Number of skills extracted")
    experience_count: int = Field(..., description="Number of work experiences")
    total_experience_years: int
    parse_quality_score: Optional[int]
    parsed_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True
