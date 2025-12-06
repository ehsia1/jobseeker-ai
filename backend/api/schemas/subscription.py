"""Subscription and usage Pydantic schemas."""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class SubscriptionTierEnum(str, Enum):
    """Subscription tier enum for API."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    POWER = "power"


class UsageActionTypeEnum(str, Enum):
    """Usage action types for API."""
    PROPOSAL_GENERATE = "proposal_generate"
    PROPOSAL_ENHANCE = "proposal_enhance"
    JD_PARSE = "jd_parse"
    RESUME_PARSE = "resume_parse"
    JOB_SEARCH = "job_search"


# --- Tier Info ---

class TierFeatures(BaseModel):
    """Features available in a subscription tier."""
    proposal_tones: List[str]
    proposal_enhance: bool
    auto_apply: bool
    priority_support: bool
    analytics: bool


class TierLimits(BaseModel):
    """Limits for a subscription tier."""
    proposals_per_month: int = Field(..., description="Use -1 for unlimited")
    jd_parses_per_month: int = Field(..., description="Use -1 for unlimited")
    job_searches_per_day: int = Field(..., description="Use -1 for unlimited")
    resume_uploads: int = Field(..., description="Use -1 for unlimited")
    features: TierFeatures


class TierInfo(BaseModel):
    """Complete tier information."""
    id: SubscriptionTierEnum
    name: str
    price_cents: int
    price_display: str
    limits: TierLimits
    popular: bool = False


# --- Subscription ---

class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    tier: SubscriptionTierEnum = SubscriptionTierEnum.FREE


class SubscriptionRead(SubscriptionBase):
    """Subscription read schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    # Stripe info (masked for security)
    has_stripe_customer: bool = False
    has_active_subscription: bool = False

    # Billing period
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None

    # Cancellation status
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None

    # Usage counts
    proposal_count: int = 0
    jd_parse_count: int = 0
    job_search_count_today: int = 0

    # Reset dates
    usage_reset_date: Optional[date] = None
    daily_reset_date: Optional[date] = None

    created_at: datetime
    updated_at: datetime


class SubscriptionWithUsage(SubscriptionRead):
    """Subscription with computed usage info."""
    # Computed usage remaining
    proposals_remaining: int = Field(..., description="-1 means unlimited")
    jd_parses_remaining: int = Field(..., description="-1 means unlimited")
    searches_remaining_today: int = Field(..., description="-1 means unlimited")

    # Tier info
    tier_limits: TierLimits
    is_active: bool = True


# --- Usage ---

class UsageLogRead(BaseModel):
    """Usage log entry."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_type: UsageActionTypeEnum
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: Optional[int] = None
    cost_cents: Optional[int] = None
    created_at: datetime


class UsageStats(BaseModel):
    """Current usage statistics."""
    tier: SubscriptionTierEnum
    is_active: bool

    # Current period usage
    proposals_used: int
    proposals_limit: int = Field(..., description="-1 means unlimited")
    proposals_remaining: int = Field(..., description="-1 means unlimited")

    jd_parses_used: int
    jd_parses_limit: int = Field(..., description="-1 means unlimited")
    jd_parses_remaining: int = Field(..., description="-1 means unlimited")

    job_searches_used_today: int
    job_searches_limit_daily: int = Field(..., description="-1 means unlimited")
    job_searches_remaining_today: int = Field(..., description="-1 means unlimited")

    # Reset info
    monthly_reset_date: Optional[date] = None
    daily_reset_date: Optional[date] = None

    # Available features
    features: TierFeatures


# --- Stripe Checkout ---

class CreateCheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    tier: SubscriptionTierEnum = Field(..., description="Target subscription tier")
    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect if payment is cancelled")


class CreateCheckoutResponse(BaseModel):
    """Response with checkout session URL."""
    checkout_url: str
    session_id: str


class CreatePortalRequest(BaseModel):
    """Request to create a Stripe customer portal session."""
    return_url: str = Field(..., description="URL to return to after portal session")


class CreatePortalResponse(BaseModel):
    """Response with portal session URL."""
    portal_url: str


# --- Subscription Management ---

class UpgradeRequest(BaseModel):
    """Request to upgrade subscription."""
    tier: SubscriptionTierEnum


class CancelRequest(BaseModel):
    """Request to cancel subscription."""
    at_period_end: bool = Field(
        True,
        description="If true, cancels at end of billing period. If false, cancels immediately."
    )


class SubscriptionActionResponse(BaseModel):
    """Response for subscription actions."""
    success: bool
    message: str
    subscription: Optional[SubscriptionRead] = None


# --- Pricing Page ---

class PricingResponse(BaseModel):
    """Pricing page data."""
    tiers: List[TierInfo]
    current_tier: Optional[SubscriptionTierEnum] = None
    stripe_publishable_key: Optional[str] = None
