"""UserFeedback Pydantic schemas."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class UserFeedbackBase(BaseModel):
    """Base user feedback schema."""
    action: str = Field(..., pattern="^(viewed|saved|applied|rejected|interviewed|hired|clicked)$")
    feedback_text: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class UserFeedbackCreate(UserFeedbackBase):
    """User feedback creation schema."""
    job_id: UUID
    match_id: UUID


class UserFeedbackRead(UserFeedbackBase):
    """User feedback read schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    job_id: UUID
    match_id: UUID
    feedback_type: Optional[str]
    created_at: datetime
    
    # Computed properties
    is_positive_signal: bool
    is_negative_signal: bool
    engagement_weight: float