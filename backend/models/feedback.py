"""User feedback model for learning and improvement."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class UserFeedback(Base):
    """User feedback on job matches for ML learning."""
    
    __tablename__ = "user_feedback"
    __table_args__ = {"schema": "jobseeker"}
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.jobs.id", ondelete="CASCADE"), nullable=False)
    match_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.job_matches.id", ondelete="CASCADE"), nullable=False)
    
    # Action taken by user
    action = Column(String(50), nullable=False, index=True)
    # Actions: "viewed", "saved", "applied", "rejected", "interviewed", "hired", "clicked"
    
    # Feedback classification
    feedback_type = Column(String(50), index=True)  # "positive", "negative", "neutral"
    feedback_text = Column(Text)  # Optional text feedback from user
    
    # Additional feedback metadata
    feedback_metadata = Column(JSONB, nullable=False, default=dict)  # Context, A/B test info, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    job = relationship("Job")
    match = relationship("JobMatch", back_populates="feedback")
    
    @property
    def is_positive_signal(self) -> bool:
        """Check if this feedback indicates user interest."""
        positive_actions = {"saved", "applied", "interviewed", "hired"}
        return self.action in positive_actions
    
    @property
    def is_negative_signal(self) -> bool:
        """Check if this feedback indicates user disinterest."""
        negative_actions = {"rejected"}
        return self.action in negative_actions
    
    @property
    def engagement_weight(self) -> float:
        """Get weight for this feedback in ML training."""
        weights = {
            "viewed": 0.1,
            "clicked": 0.2,
            "saved": 0.5,
            "applied": 1.0,
            "rejected": -0.5,
            "interviewed": 2.0,
            "hired": 3.0,
        }
        return weights.get(self.action, 0.0)
    
    @classmethod
    def create_from_action(
        cls, 
        user_id: UUID, 
        job_id: UUID, 
        match_id: UUID, 
        action: str,
        feedback_text: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> "UserFeedback":
        """Create feedback from user action."""
        
        # Classify feedback type based on action
        if action in {"saved", "applied", "interviewed", "hired"}:
            feedback_type = "positive"
        elif action in {"rejected"}:
            feedback_type = "negative" 
        else:
            feedback_type = "neutral"
        
        return cls(
            user_id=user_id,
            job_id=job_id,
            match_id=match_id,
            action=action,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            metadata=metadata or {}
        )