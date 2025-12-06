"""Schemas for JD Parser API."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ParseJDRequest(BaseModel):
    """Request to parse a job description."""

    text: str = Field(..., min_length=50, description="Raw job description text")


class ParsedJDResponse(BaseModel):
    """Parsed job description data."""

    title: Optional[str] = None
    company: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    experience_years_min: Optional[int] = None
    experience_years_max: Optional[int] = None
    compensation_min: Optional[float] = None
    compensation_max: Optional[float] = None
    compensation_type: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    employment_type: Optional[str] = None
    key_requirements: List[str] = Field(default_factory=list)
    keywords_to_emphasize: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)


class ScoreBreakdownResponse(BaseModel):
    """Score breakdown for job match."""

    total_score: float
    semantic_similarity: float
    skill_match: float
    experience_match: float
    compensation_match: float
    location_match: float
    freshness_score: float
    preference_match: float


class JDParseResponse(BaseModel):
    """Full response from JD parsing."""

    parsed: ParsedJDResponse
    match_score: Optional[ScoreBreakdownResponse] = None
    explanation: Optional[str] = None


class ExtractKeywordsRequest(BaseModel):
    """Request to extract keywords from JD."""

    text: str = Field(..., min_length=50, description="Raw job description text")


class ExtractKeywordsResponse(BaseModel):
    """Response with extracted keywords."""

    keywords: List[str]
