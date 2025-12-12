"""Recommendation engine Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Response schemas
class ScoreBreakdownResponse(BaseModel):
    """Breakdown of how a job score was calculated."""

    semantic_similarity: float = Field(..., description="Semantic match score (0-100)")
    skill_match: float = Field(..., description="Skill match score (0-100)")
    experience_match: float = Field(..., description="Experience match score (0-100)")
    compensation_match: float = Field(..., description="Compensation match score (0-100)")
    location_match: float = Field(..., description="Location/remote match score (0-100)")
    freshness_score: float = Field(..., description="Job freshness score (0-100)")
    preference_match: float = Field(..., description="User preference match score (0-100)")
    total_score: float = Field(..., description="Total weighted score (0-100)")


class MLAdjustmentResponse(BaseModel):
    """ML adjustment details for a recommendation."""

    skill_boost: float = Field(default=0.0, description="Boost from skill preferences")
    company_boost: float = Field(default=0.0, description="Boost from company preferences")
    preference_boost: float = Field(default=0.0, description="Boost from implicit preferences")
    remote_boost: Optional[float] = Field(default=None, description="Boost from remote preference")
    pay_preference_boost: Optional[float] = Field(default=None, description="Boost from pay preference")
    confidence: float = Field(..., description="Model confidence (0-1)")
    insufficient_data: bool = Field(default=False, description="Whether ML had enough data")
    matched_skill_preferences: List[tuple] = Field(
        default_factory=list,
        description="Skills that matched user preferences"
    )


class JobRecommendationResponse(BaseModel):
    """A single job recommendation with scoring details."""

    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    job_title: str
    company: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    rate_min: Optional[float] = None
    rate_max: Optional[float] = None
    rate_type: Optional[str] = None
    skills: List[str] = Field(default_factory=list)

    # Scoring
    final_score: float = Field(..., description="Final score after ML adjustment")
    base_score: float = Field(..., description="Base score before ML adjustment")
    ml_adjustment: float = Field(default=0.0, description="ML score adjustment")
    confidence: float = Field(default=0.0, description="Model confidence")

    # Detailed breakdown (optional)
    score_breakdown: Optional[Dict[str, float]] = None
    ml_factors: Optional[Dict[str, Any]] = None

    # Explanation
    explanation: Optional[str] = None


class RecommendationListResponse(BaseModel):
    """List of job recommendations."""

    recommendations: List[JobRecommendationResponse]
    total: int
    model_confidence: float = Field(..., description="Overall model confidence for this user")
    personalization_enabled: bool = Field(
        ...,
        description="Whether personalization is active"
    )


class UserPreferencesResponse(BaseModel):
    """User's learned preferences."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    confidence_score: float = Field(..., description="Model confidence (0-1)")
    total_interactions: int = Field(..., description="Total feedback interactions")
    positive_samples: int = Field(..., description="Number of positive feedback samples")
    negative_samples: int = Field(..., description="Number of negative feedback samples")

    # Learned preferences
    skill_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Skill preference scores (-1 to 1)"
    )
    company_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Company preference scores (-1 to 1)"
    )
    learned_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Implicit preferences (remote, pay, etc.)"
    )
    weight_adjustments: Dict[str, float] = Field(
        default_factory=dict,
        description="Scoring weight multipliers"
    )

    last_trained_at: Optional[datetime] = None
    model_version: str = Field(default="1.0.0")


class RecommendationAnalyticsResponse(BaseModel):
    """Analytics on recommendation performance."""

    total_recommendations: int
    view_rate: float = Field(..., description="Percentage of recommendations viewed")
    click_rate: float = Field(..., description="Percentage of recommendations clicked")
    save_rate: float = Field(..., description="Percentage of recommendations saved")
    apply_rate: float = Field(..., description="Percentage of recommendations applied to")
    avg_base_score: float
    avg_ml_adjustment: float
    avg_final_score: float
    days_analyzed: Optional[int] = None


class SimilarUserResponse(BaseModel):
    """A similar user for collaborative filtering."""

    user_id: UUID
    similarity_score: float = Field(..., description="Similarity score (0-1)")


class CollaborativeRecommendationResponse(BaseModel):
    """A recommendation from collaborative filtering."""

    job_id: str
    job_title: str
    company: Optional[str] = None
    source_user_similarity: float
    source_action: str
    reason: str


class CollaborativeRecommendationsResponse(BaseModel):
    """List of collaborative filtering recommendations."""

    recommendations: List[CollaborativeRecommendationResponse]
    similar_users_found: int


class FeedbackStatisticsResponse(BaseModel):
    """User feedback statistics."""

    action_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of each action type"
    )
    total_interactions: int
    total_engagement_score: float
    positive_actions: int
    negative_actions: int
    engagement_ratio: float = Field(
        ...,
        description="Ratio of positive to total actions"
    )
    days_analyzed: int


# Request schemas
class RecordFeedbackRequest(BaseModel):
    """Request to record user feedback."""

    job_id: UUID = Field(..., description="Job ID")
    match_id: UUID = Field(..., description="JobMatch ID")
    action: str = Field(
        ...,
        description="Action taken: viewed, clicked, saved, applied, rejected, interviewed, hired"
    )
    feedback_text: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional text feedback"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional additional context"
    )


class UpdatePreferencesRequest(BaseModel):
    """Request to force update user preferences."""

    force_update: bool = Field(
        default=False,
        description="Force update even if not enough new data"
    )


class GetRecommendationsRequest(BaseModel):
    """Request parameters for getting recommendations."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of recommendations"
    )
    min_score: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Minimum score threshold"
    )
    include_breakdown: bool = Field(
        default=False,
        description="Include detailed score breakdown"
    )


# Health check
class RecommendationHealthResponse(BaseModel):
    """Health check response for recommendation service."""

    status: str
    ml_enabled: bool
    supported_actions: List[str]
    min_interactions_for_personalization: int
