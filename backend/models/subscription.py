"""Subscription and usage tracking models."""

from datetime import datetime, date
from enum import Enum as PyEnum
from typing import Dict, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Date, Integer, String,
    ForeignKey, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class SubscriptionTier(str, PyEnum):
    """Subscription tier levels."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    POWER = "power"


class UsageActionType(str, PyEnum):
    """Types of actions that count against usage limits."""
    PROPOSAL_GENERATE = "proposal_generate"
    PROPOSAL_ENHANCE = "proposal_enhance"
    JD_PARSE = "jd_parse"
    RESUME_PARSE = "resume_parse"
    JOB_SEARCH = "job_search"


# Tier limits configuration
TIER_LIMITS: Dict[str, Dict] = {
    "free": {
        "proposals_per_month": 5,
        "jd_parses_per_month": 10,
        "job_searches_per_day": 3,
        "resume_uploads": 1,
        "features": {
            "proposal_tones": ["medium"],  # Only medium tone
            "proposal_enhance": False,
            "auto_apply": False,
            "priority_support": False,
            "analytics": False,
        }
    },
    "starter": {
        "proposals_per_month": 50,
        "jd_parses_per_month": 100,
        "job_searches_per_day": 20,
        "resume_uploads": 3,
        "features": {
            "proposal_tones": ["short", "medium", "full"],
            "proposal_enhance": True,
            "auto_apply": False,
            "priority_support": False,
            "analytics": True,
        }
    },
    "pro": {
        "proposals_per_month": float("inf"),
        "jd_parses_per_month": float("inf"),
        "job_searches_per_day": float("inf"),
        "resume_uploads": 10,
        "features": {
            "proposal_tones": ["short", "medium", "full"],
            "proposal_enhance": True,
            "auto_apply": False,
            "priority_support": True,
            "analytics": True,
        }
    },
    "power": {
        "proposals_per_month": float("inf"),
        "jd_parses_per_month": float("inf"),
        "job_searches_per_day": float("inf"),
        "resume_uploads": float("inf"),
        "features": {
            "proposal_tones": ["short", "medium", "full"],
            "proposal_enhance": True,
            "auto_apply": True,  # Auto-apply to matching jobs
            "priority_support": True,
            "analytics": True,
        }
    },
}

# Pricing in cents (for Stripe)
TIER_PRICING = {
    "free": 0,
    "starter": 999,      # $9.99/month
    "pro": 2999,         # $29.99/month
    "power": 7999,       # $79.99/month
}


class Subscription(Base):
    """User subscription and billing information."""

    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Subscription tier
    tier = Column(
        Enum(SubscriptionTier, name="subscription_tier", schema="jobseeker"),
        nullable=False,
        default=SubscriptionTier.FREE
    )

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Billing period
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    # Usage counters (reset monthly)
    proposal_count = Column(Integer, default=0, nullable=False)
    jd_parse_count = Column(Integer, default=0, nullable=False)
    job_search_count_today = Column(Integer, default=0, nullable=False)

    # Reset dates
    usage_reset_date = Column(Date, nullable=True)  # When monthly counters reset
    daily_reset_date = Column(Date, nullable=True)  # When daily counters reset

    # Extra data
    extra_data = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscription")
    usage_logs = relationship("UsageLog", back_populates="subscription", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.tier == SubscriptionTier.FREE:
            return True
        if not self.current_period_end:
            return False
        return datetime.now(self.current_period_end.tzinfo) < self.current_period_end

    @property
    def tier_limits(self) -> Dict:
        """Get limits for current tier."""
        return TIER_LIMITS.get(self.tier.value, TIER_LIMITS["free"])

    @property
    def proposals_remaining(self) -> int:
        """Get remaining proposals for current period."""
        limit = self.tier_limits.get("proposals_per_month", 5)
        if limit == float("inf"):
            return -1  # Unlimited
        return max(0, int(limit) - self.proposal_count)

    @property
    def jd_parses_remaining(self) -> int:
        """Get remaining JD parses for current period."""
        limit = self.tier_limits.get("jd_parses_per_month", 10)
        if limit == float("inf"):
            return -1  # Unlimited
        return max(0, int(limit) - self.jd_parse_count)

    @property
    def searches_remaining_today(self) -> int:
        """Get remaining job searches for today."""
        limit = self.tier_limits.get("job_searches_per_day", 3)
        if limit == float("inf"):
            return -1  # Unlimited
        return max(0, int(limit) - self.job_search_count_today)

    def has_feature(self, feature: str) -> bool:
        """Check if current tier includes a feature."""
        features = self.tier_limits.get("features", {})
        return features.get(feature, False)

    def can_use_tone(self, tone: str) -> bool:
        """Check if current tier can use a proposal tone."""
        features = self.tier_limits.get("features", {})
        allowed_tones = features.get("proposal_tones", ["medium"])
        return tone in allowed_tones


class UsageLog(Base):
    """Log of usage actions for analytics and auditing."""

    __tablename__ = "usage_logs"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Action details
    action_type = Column(
        Enum(UsageActionType, name="usage_action_type", schema="jobseeker"),
        nullable=False
    )

    # Additional context
    extra_data = Column(JSONB, nullable=False, default=dict)  # e.g., {"job_id": "...", "tone": "medium"}

    # Cost tracking (for internal analytics)
    tokens_used = Column(Integer, nullable=True)  # LLM tokens consumed
    cost_cents = Column(Integer, nullable=True)  # Estimated cost in cents

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    subscription = relationship("Subscription", back_populates="usage_logs")
