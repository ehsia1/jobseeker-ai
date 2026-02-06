"""Client/Employer risk assessment models."""

from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(str, Enum):
    """Categories of risk factors."""
    PAYMENT = "payment"  # Payment-related red flags
    EXPECTATIONS = "expectations"  # Unrealistic expectations
    COMMUNICATION = "communication"  # Communication red flags
    COMPANY = "company"  # Company legitimacy concerns
    SCOPE = "scope"  # Scope creep indicators
    LEGAL = "legal"  # Legal/contract concerns
    REPUTATION = "reputation"  # Company reputation signals


class ClientRiskAssessment(Base):
    """Risk assessment for a job posting/client."""

    __tablename__ = "client_risk_assessments"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.jobs.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Overall risk assessment
    risk_score = Column(Integer, nullable=False, default=0)  # 0-100, higher = more risky
    risk_level = Column(String(20), nullable=False, default="low")  # low, medium, high, critical

    # Breakdown by category
    risk_breakdown = Column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "payment": {"score": 20, "factors": ["Vague payment terms"]},
    #   "expectations": {"score": 15, "factors": ["Unrealistic timeline"]},
    #   ...
    # }

    # Individual red flags detected
    red_flags = Column(JSONB, nullable=False, default=list)
    # Structure:
    # [
    #   {"category": "payment", "flag": "No budget mentioned", "severity": "medium", "confidence": 0.85},
    #   {"category": "scope", "flag": "Scope unclear", "severity": "low", "confidence": 0.7},
    # ]

    # Positive signals detected
    green_flags = Column(JSONB, nullable=False, default=list)
    # Structure:
    # [
    #   {"category": "company", "flag": "Verified employer", "confidence": 0.95},
    #   {"category": "payment", "flag": "Clear budget range", "confidence": 0.9},
    # ]

    # Analysis metadata
    analysis_method = Column(String(50), nullable=False, default="llm")  # "llm", "rules", "hybrid"
    model_used = Column(String(100))  # e.g., "claude-3-5-sonnet"
    analysis_version = Column(String(20), default="1.0")

    # External data used
    external_data_sources = Column(JSONB, nullable=False, default=list)
    # e.g., ["glassdoor", "bbb", "linkedin"]

    # Explanation for the user
    summary = Column(Text)  # Human-readable summary
    recommendations = Column(JSONB, nullable=False, default=list)
    # ["Clarify payment terms before accepting", "Request milestone-based payments"]

    # Company-level aggregation (for repeat clients)
    company_name = Column(String(255), index=True)
    company_risk_trend = Column(String(20))  # "improving", "stable", "declining"

    # Timestamps
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True))  # When to re-analyze
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    job = relationship("Job", backref="risk_assessment")

    @property
    def is_expired(self) -> bool:
        """Check if assessment needs to be refreshed."""
        from datetime import datetime, timezone
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def risk_level_enum(self) -> RiskLevel:
        """Get risk level as enum."""
        try:
            return RiskLevel(self.risk_level)
        except ValueError:
            return RiskLevel.LOW

    @property
    def top_concerns(self) -> list:
        """Get top 3 risk concerns sorted by severity."""
        if not self.red_flags:
            return []

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_flags = sorted(
            self.red_flags,
            key=lambda x: (severity_order.get(x.get("severity", "low"), 3), -x.get("confidence", 0))
        )
        return sorted_flags[:3]

    @property
    def category_scores(self) -> dict:
        """Get risk scores by category."""
        return {
            category: data.get("score", 0)
            for category, data in (self.risk_breakdown or {}).items()
        }

    @classmethod
    def calculate_risk_level(cls, score: int) -> str:
        """Calculate risk level from score."""
        if score >= 75:
            return RiskLevel.CRITICAL.value
        elif score >= 50:
            return RiskLevel.HIGH.value
        elif score >= 25:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value


class CompanyRiskProfile(Base):
    """Aggregated risk profile for a company across all job postings."""

    __tablename__ = "company_risk_profiles"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Company identification
    company_name = Column(String(255), nullable=False, index=True)
    company_name_normalized = Column(String(255), nullable=False, index=True)  # lowercase, trimmed

    # Aggregated scores
    average_risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="low")
    total_jobs_analyzed = Column(Integer, default=0)

    # Risk pattern tracking
    common_red_flags = Column(JSONB, nullable=False, default=list)
    # [{"flag": "Vague requirements", "count": 5, "percentage": 50}]

    common_green_flags = Column(JSONB, nullable=False, default=list)

    # Trend over time
    risk_history = Column(JSONB, nullable=False, default=list)
    # [{"date": "2024-01", "score": 35}, {"date": "2024-02", "score": 30}]

    risk_trend = Column(String(20), default="stable")  # improving, stable, declining

    # User feedback aggregation
    user_reports = Column(Integer, default=0)
    positive_outcomes = Column(Integer, default=0)  # Jobs that led to successful work
    negative_outcomes = Column(Integer, default=0)  # Jobs that led to issues

    # External reputation
    external_ratings = Column(JSONB, nullable=False, default=dict)
    # {"glassdoor": 3.5, "indeed": 3.2, "bbb": "A+"}

    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @classmethod
    def normalize_company_name(cls, name: str) -> str:
        """Normalize company name for matching."""
        import re
        if not name:
            return ""
        # Lowercase, remove common suffixes, normalize whitespace
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+(inc\.?|llc\.?|ltd\.?|corp\.?|co\.?)$', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
