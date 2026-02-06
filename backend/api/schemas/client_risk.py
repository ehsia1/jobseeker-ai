"""Pydantic schemas for Client Risk API."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class RedFlag(BaseModel):
    """A detected red flag."""
    category: str
    flag: str
    severity: str  # low, medium, high, critical
    confidence: float = Field(ge=0, le=1)
    source: Optional[str] = None  # pattern, llm, field


class GreenFlag(BaseModel):
    """A detected positive signal."""
    category: str
    flag: str
    confidence: float = Field(ge=0, le=1)
    source: Optional[str] = None


class RiskBreakdownCategory(BaseModel):
    """Risk breakdown for a single category."""
    score: int = Field(ge=0, le=100)
    factors: List[str]


class ClientRiskResponse(BaseModel):
    """Response for client risk assessment."""
    id: UUID
    job_id: UUID

    # Overall assessment
    risk_score: int = Field(ge=0, le=100)
    risk_level: str  # low, medium, high, critical

    # Detailed breakdown
    risk_breakdown: Dict[str, RiskBreakdownCategory]
    red_flags: List[RedFlag]
    green_flags: List[GreenFlag]

    # User-friendly content
    summary: Optional[str] = None
    recommendations: List[str]

    # Company context
    company_name: Optional[str] = None
    company_risk_trend: Optional[str] = None

    # Metadata
    analysis_method: str
    analyzed_at: datetime

    class Config:
        from_attributes = True


class ClientRiskBrief(BaseModel):
    """Brief risk info for list views."""
    job_id: UUID
    risk_score: int
    risk_level: str
    top_concern: Optional[str] = None
    analyzed_at: datetime

    class Config:
        from_attributes = True


class CompanyRiskProfileResponse(BaseModel):
    """Response for company risk profile."""
    id: UUID
    company_name: str

    # Aggregated scores
    average_risk_score: int
    risk_level: str
    total_jobs_analyzed: int

    # Patterns
    common_red_flags: List[Dict[str, Any]]
    common_green_flags: List[Dict[str, Any]]

    # Trend
    risk_trend: Optional[str] = None
    risk_history: List[Dict[str, Any]]

    # User feedback
    user_reports: int
    positive_outcomes: int
    negative_outcomes: int

    # External data
    external_ratings: Dict[str, Any]

    first_seen: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


class AnalyzeJobRequest(BaseModel):
    """Request to analyze a job for risk."""
    job_id: UUID
    force_refresh: bool = False


class BatchAnalyzeRequest(BaseModel):
    """Request to analyze multiple jobs."""
    job_ids: List[UUID]


class BatchAnalyzeResponse(BaseModel):
    """Response for batch analysis."""
    analyzed: int
    failed: int
    results: List[ClientRiskBrief]
