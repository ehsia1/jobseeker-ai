"""Pydantic schemas for Proposal API endpoints."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProposalToneEnum(str, Enum):
    """Proposal tone options."""

    SHORT = "short"
    MEDIUM = "medium"
    FULL = "full"


class EnhancementType(str, Enum):
    """Proposal enhancement types."""

    ADD_KEYWORDS = "add_keywords"
    IMPROVE_TONE = "improve_tone"
    ADD_METRICS = "add_metrics"
    SHORTEN = "shorten"
    EXPAND = "expand"


class ParsedJDInput(BaseModel):
    """Parsed JD data for proposal generation without a saved job."""

    title: Optional[str] = None
    company: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    key_requirements: List[str] = Field(default_factory=list)
    keywords_to_emphasize: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    remote: bool = False
    raw_text: str = ""


class GenerateProposalRequest(BaseModel):
    """Request to generate a new proposal."""

    job_id: Optional[str] = Field(
        None, description="UUID of a saved job from the database"
    )
    parsed_jd: Optional[ParsedJDInput] = Field(
        None, description="Parsed JD data (use if job not saved)"
    )
    tone: ProposalToneEnum = Field(
        ProposalToneEnum.MEDIUM, description="Proposal length/style"
    )
    additional_context: Optional[str] = Field(
        None,
        max_length=1000,
        description="Extra context to incorporate (e.g., specific points to mention)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "parsed_jd": {
                        "title": "Senior Python Developer",
                        "company": "TechCorp",
                        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                        "keywords_to_emphasize": ["async", "API design", "scaling"],
                    },
                    "tone": "medium",
                }
            ]
        }


class GenerateAllTonesRequest(BaseModel):
    """Request to generate proposals in all tones."""

    job_id: Optional[str] = Field(
        None, description="UUID of a saved job from the database"
    )
    parsed_jd: Optional[ParsedJDInput] = Field(
        None, description="Parsed JD data (use if job not saved)"
    )
    additional_context: Optional[str] = Field(
        None, max_length=1000, description="Extra context to incorporate"
    )


class EnhanceProposalRequest(BaseModel):
    """Request to enhance an existing proposal."""

    original_proposal: str = Field(
        ..., min_length=20, max_length=5000, description="The proposal text to enhance"
    )
    job_id: Optional[str] = Field(None, description="UUID of a saved job (optional)")
    parsed_jd: Optional[ParsedJDInput] = Field(
        None, description="Parsed JD for context (optional)"
    )
    enhancements: List[EnhancementType] = Field(
        default=[EnhancementType.IMPROVE_TONE, EnhancementType.ADD_KEYWORDS],
        description="Types of enhancements to apply",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "original_proposal": "Hi, I can do this job. I have 5 years of experience with Python.",
                    "enhancements": ["improve_tone", "add_keywords", "add_metrics"],
                }
            ]
        }


class ProposalResponse(BaseModel):
    """Generated proposal response."""

    content: str = Field(..., description="The generated proposal text")
    tone: str = Field(..., description="The tone used (short/medium/full)")
    word_count: int = Field(..., description="Word count of the proposal")
    keywords_used: List[str] = Field(
        default_factory=list, description="Keywords from JD that were incorporated"
    )
    experience_highlighted: List[str] = Field(
        default_factory=list, description="Experience/achievements mentioned"
    )


class AllTonesResponse(BaseModel):
    """Response with proposals in all three tones."""

    short: ProposalResponse
    medium: ProposalResponse
    full: ProposalResponse


class EnhanceProposalResponse(BaseModel):
    """Enhanced proposal response."""

    enhanced_proposal: str = Field(..., description="The enhanced proposal text")
    tone: str = Field(..., description="The tone of the result")
    word_count: int = Field(..., description="Word count of enhanced proposal")
    keywords_used: List[str] = Field(
        default_factory=list, description="Keywords incorporated"
    )
    enhancements_applied: List[str] = Field(
        ..., description="List of enhancements that were applied"
    )
