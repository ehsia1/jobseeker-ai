"""Pydantic schemas for A/B testing API endpoints."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


# ============= Proposal Variant Schemas =============


class ProposalVariantBase(BaseModel):
    """Base proposal variant data."""

    content: str = Field(..., description="Proposal content text")
    variant_name: Optional[str] = Field(None, description="Human-readable name for the variant")
    tone: Optional[str] = Field(None, description="Proposal tone (short, medium, full)")
    style: Optional[str] = Field(
        None, description="Cover letter style (traditional, modern, creative, executive)"
    )
    length: Optional[str] = Field(
        None, description="Length option (concise, standard, detailed)"
    )


class ProposalVariantCreate(ProposalVariantBase):
    """Request to create a proposal variant."""

    job_match_id: Optional[UUID] = Field(None, description="Associated job match ID")
    ab_test_id: Optional[UUID] = Field(None, description="Associated A/B test ID")
    variant_label: Optional[str] = Field(
        None, description="Variant label for A/B testing (A or B)"
    )
    generation_method: Optional[str] = Field(
        None, description="How the proposal was generated"
    )
    model_used: Optional[str] = Field(None, description="AI model used for generation")
    keywords_used: Optional[List[str]] = Field(
        None, description="Keywords included in the proposal"
    )
    ats_score: Optional[int] = Field(None, ge=0, le=100, description="ATS score if calculated")
    is_control: bool = Field(False, description="Is this the control variant")


class ProposalVariantResponse(ProposalVariantBase):
    """Proposal variant response."""

    id: UUID
    user_id: UUID
    job_match_id: Optional[UUID]
    ab_test_id: Optional[UUID]

    # Generation metadata
    variant_label: Optional[str]
    generation_method: Optional[str]
    model_used: Optional[str]
    word_count: Optional[int]
    keywords_used: List[str] = []
    ats_score: Optional[int]

    # A/B test tracking
    is_control: bool
    is_selected: bool

    # Outcome tracking
    was_sent: bool
    sent_at: Optional[datetime]
    got_response: bool
    response_at: Optional[datetime]
    got_interview: bool
    interview_at: Optional[datetime]
    got_offer: bool
    offer_at: Optional[datetime]

    # Computed fields
    outcome_score: int = Field(..., description="Outcome score (0-4)")
    days_to_response: Optional[int]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProposalVariantUpdate(BaseModel):
    """Request to update a variant."""

    content: Optional[str] = None
    variant_name: Optional[str] = None


class RecordOutcomeRequest(BaseModel):
    """Request to record an outcome for a variant."""

    outcome_type: str = Field(
        ..., description="Type of outcome: response, interview, or offer"
    )


# ============= A/B Test Schemas =============


class ABTestBase(BaseModel):
    """Base A/B test data."""

    name: str = Field(..., description="Test name (e.g., 'Formal vs Casual Tone')")
    description: Optional[str] = Field(None, description="Test description")
    test_type: str = Field(
        ..., description="Type of test: tone, style, length, or custom"
    )


class ABTestCreate(ABTestBase):
    """Request to create an A/B test."""

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Test parameters defining variant configurations",
        json_schema_extra={
            "example": {
                "variant_a": {"tone": "formal", "style": "traditional"},
                "variant_b": {"tone": "casual", "style": "modern"},
            }
        },
    )
    target_sample_size: int = Field(
        10, ge=1, le=100, description="Target number of proposals per variant"
    )


class ABTestResponse(ABTestBase):
    """A/B test response."""

    id: UUID
    user_id: UUID
    status: str

    # Configuration
    parameters: Dict[str, Any]
    target_sample_size: int
    current_sample_size_a: int
    current_sample_size_b: int

    # Timing
    started_at: Optional[datetime]
    ended_at: Optional[datetime]

    # Results
    results: Dict[str, Any]
    winner_variant: Optional[str]

    # Computed metrics
    variant_a_metrics: Dict[str, Any] = Field(default_factory=dict)
    variant_b_metrics: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ABTestWithVariants(ABTestResponse):
    """A/B test response with associated variants."""

    variants: List[ProposalVariantResponse] = []


class ABTestUpdate(BaseModel):
    """Request to update an A/B test."""

    name: Optional[str] = None
    description: Optional[str] = None
    target_sample_size: Optional[int] = Field(None, ge=1, le=100)


# ============= Analytics Schemas =============


class ToneStyleStats(BaseModel):
    """Statistics for a specific tone or style."""

    total: int
    sent: int
    responses: int
    interviews: int
    offers: int
    response_rate: float
    interview_rate: float


class VariantStatsResponse(BaseModel):
    """User's overall variant statistics."""

    total_variants: int
    sent_count: int
    response_count: int
    interview_count: int
    offer_count: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    by_tone: Dict[str, ToneStyleStats]
    by_style: Dict[str, ToneStyleStats]


# ============= Quick Generate Schemas =============


class GenerateABVariantsRequest(BaseModel):
    """Request to generate A/B test variants for a job."""

    job_match_id: UUID = Field(..., description="Job match to generate variants for")
    ab_test_id: Optional[UUID] = Field(
        None, description="Link variants to an existing A/B test"
    )
    variant_a_config: Dict[str, Any] = Field(
        ...,
        description="Configuration for variant A",
        json_schema_extra={"example": {"tone": "formal"}},
    )
    variant_b_config: Dict[str, Any] = Field(
        ...,
        description="Configuration for variant B",
        json_schema_extra={"example": {"tone": "casual"}},
    )


class GenerateABVariantsResponse(BaseModel):
    """Response after generating A/B variants."""

    variant_a: ProposalVariantResponse
    variant_b: ProposalVariantResponse
    ab_test_id: Optional[UUID] = None
