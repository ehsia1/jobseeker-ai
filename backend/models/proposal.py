"""Proposal variant and A/B testing models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class ProposalTone(str, Enum):
    """Proposal tone/length options."""
    SHORT = "short"
    MEDIUM = "medium"
    FULL = "full"


class ProposalStyle(str, Enum):
    """Cover letter style options."""
    TRADITIONAL = "traditional"
    MODERN = "modern"
    CREATIVE = "creative"
    EXECUTIVE = "executive"


class ABTestStatus(str, Enum):
    """A/B test status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ProposalVariant(Base):
    """Stores different proposal versions for A/B testing and version history."""

    __tablename__ = "proposal_variants"
    __table_args__ = (
        Index("ix_proposal_variants_job_match", "job_match_id"),
        Index("ix_proposal_variants_ab_test", "ab_test_id"),
        Index("ix_proposal_variants_user", "user_id"),
        {"schema": "jobseeker"},
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_match_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.job_matches.id", ondelete="CASCADE"),
        nullable=True,  # Can be null for template variants
    )
    ab_test_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.ab_tests.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Content
    content = Column(Text, nullable=False)
    variant_name = Column(String(100))  # "Version A", "Formal Tone", etc.

    # Generation parameters
    tone = Column(String(20))  # short, medium, full (proposal service)
    style = Column(String(20))  # traditional, modern, creative, executive (cover letter)
    length = Column(String(20))  # concise, standard, detailed

    # Metadata
    generation_method = Column(String(50))  # "proposal_service", "cover_letter_agent", "manual"
    model_used = Column(String(100))  # "gpt-4o", "claude-3-5-sonnet", etc.
    word_count = Column(Integer)
    keywords_used = Column(JSONB, default=list)  # Keywords included in variant
    ats_score = Column(Integer)  # ATS compatibility score if calculated

    # A/B Test tracking
    is_control = Column(Boolean, default=False)  # Is this the control variant in an A/B test
    is_selected = Column(Boolean, default=False)  # Was this variant selected/used
    variant_label = Column(String(10))  # "A", "B", "C" for A/B test variants

    # Performance metrics (updated when outcomes are known)
    metrics = Column(
        JSONB,
        default=dict,
        nullable=False,
    )  # {sent_at, opened_at, responded_at, interview_at, offer_at}

    # Outcome tracking
    was_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    got_response = Column(Boolean, default=False)
    response_at = Column(DateTime(timezone=True))
    got_interview = Column(Boolean, default=False)
    interview_at = Column(DateTime(timezone=True))
    got_offer = Column(Boolean, default=False)
    offer_at = Column(DateTime(timezone=True))

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="proposal_variants")
    job_match = relationship("JobMatch", back_populates="proposal_variants")
    ab_test = relationship("ABTest", back_populates="variants")

    @property
    def outcome_score(self) -> int:
        """Calculate outcome score based on how far the proposal got.

        Higher scores = better outcomes.
        0 = Not sent
        1 = Sent, no response
        2 = Got response
        3 = Got interview
        4 = Got offer
        """
        if self.got_offer:
            return 4
        if self.got_interview:
            return 3
        if self.got_response:
            return 2
        if self.was_sent:
            return 1
        return 0

    @property
    def days_to_response(self) -> Optional[int]:
        """Days from sent to first response."""
        if self.sent_at and self.response_at:
            delta = self.response_at - self.sent_at
            return delta.days
        return None


class ABTest(Base):
    """A/B test configuration and results."""

    __tablename__ = "ab_tests"
    __table_args__ = (
        Index("ix_ab_tests_user", "user_id"),
        Index("ix_ab_tests_status", "status"),
        {"schema": "jobseeker"},
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Test configuration
    name = Column(String(200), nullable=False)  # "Formal vs Casual Tone"
    description = Column(Text)
    test_type = Column(String(50), nullable=False)  # "tone", "style", "length", "custom"
    status = Column(String(20), default="draft", nullable=False)

    # Test parameters
    parameters = Column(
        JSONB,
        default=dict,
        nullable=False,
    )  # {variant_a: {tone: "formal"}, variant_b: {tone: "casual"}}

    # Target sample size
    target_sample_size = Column(Integer, default=10)  # Minimum proposals per variant
    current_sample_size_a = Column(Integer, default=0)
    current_sample_size_b = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))

    # Results (populated when test completes)
    results = Column(
        JSONB,
        default=dict,
        nullable=False,
    )  # {winner, confidence, metrics_a, metrics_b, statistical_significance}

    # Winner tracking
    winner_variant = Column(String(10))  # "A", "B", or null if inconclusive

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="ab_tests")
    variants = relationship(
        "ProposalVariant",
        back_populates="ab_test",
        cascade="all, delete-orphan",
    )

    @property
    def is_active(self) -> bool:
        """Check if test is currently active."""
        return self.status == ABTestStatus.ACTIVE.value

    @property
    def total_variants(self) -> int:
        """Count total variants in this test."""
        return len(self.variants) if self.variants else 0

    @property
    def variant_a_metrics(self) -> dict:
        """Get aggregated metrics for variant A."""
        if not self.variants:
            return {}

        variant_a = [v for v in self.variants if v.variant_label == "A"]
        return self._aggregate_variant_metrics(variant_a)

    @property
    def variant_b_metrics(self) -> dict:
        """Get aggregated metrics for variant B."""
        if not self.variants:
            return {}

        variant_b = [v for v in self.variants if v.variant_label == "B"]
        return self._aggregate_variant_metrics(variant_b)

    def _aggregate_variant_metrics(self, variants: list) -> dict:
        """Aggregate metrics across a list of variants."""
        if not variants:
            return {
                "count": 0,
                "sent": 0,
                "responses": 0,
                "interviews": 0,
                "offers": 0,
                "response_rate": 0,
                "interview_rate": 0,
                "offer_rate": 0,
            }

        sent = sum(1 for v in variants if v.was_sent)
        responses = sum(1 for v in variants if v.got_response)
        interviews = sum(1 for v in variants if v.got_interview)
        offers = sum(1 for v in variants if v.got_offer)

        return {
            "count": len(variants),
            "sent": sent,
            "responses": responses,
            "interviews": interviews,
            "offers": offers,
            "response_rate": (responses / sent * 100) if sent > 0 else 0,
            "interview_rate": (interviews / sent * 100) if sent > 0 else 0,
            "offer_rate": (offers / sent * 100) if sent > 0 else 0,
        }
