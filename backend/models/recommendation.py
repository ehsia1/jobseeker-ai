"""Models for ML-based recommendation system."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Float, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class UserPreferenceModel(Base):
    """Learned user preferences from feedback for personalized scoring."""

    __tablename__ = "user_preference_models"
    __table_args__ = (
        Index("ix_user_pref_user_id", "user_id"),
        {"schema": "jobseeker"}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Learned scoring weight adjustments (deltas from default)
    weight_adjustments = Column(JSONB, nullable=False, default=dict)
    # Example: {"skill_match": 0.05, "compensation_match": -0.03}

    # Learned feature preferences (what features correlate with positive actions)
    skill_preferences = Column(JSONB, nullable=False, default=dict)
    # Example: {"python": 0.8, "react": 0.6, "management": -0.2}

    company_preferences = Column(JSONB, nullable=False, default=dict)
    # Example: {"Google": 0.9, "Startup": 0.7}

    # User's implicit preferences learned from behavior
    learned_preferences = Column(JSONB, nullable=False, default=dict)
    # Example: {"prefers_remote": 0.95, "prefers_high_pay": 0.7, "avoids_travel": 0.8}

    # Model confidence based on amount of training data
    confidence_score = Column(Float, default=0.0, nullable=False)

    # Training data statistics
    positive_samples = Column(Integer, default=0, nullable=False)
    negative_samples = Column(Integer, default=0, nullable=False)
    total_interactions = Column(Integer, default=0, nullable=False)

    # Model metadata
    model_version = Column(String(50), default="v1", nullable=False)
    last_trained_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="preference_model")

    @property
    def has_sufficient_data(self) -> bool:
        """Check if we have enough data to make confident predictions."""
        return self.total_interactions >= 10 and self.positive_samples >= 3

    def get_skill_boost(self, skill: str) -> float:
        """Get preference boost for a specific skill."""
        return self.skill_preferences.get(skill.lower(), 0.0)

    def get_company_boost(self, company: str) -> float:
        """Get preference boost for a specific company."""
        return self.company_preferences.get(company.lower(), 0.0)


class RecommendationLog(Base):
    """Log of recommendations made for analytics and model improvement."""

    __tablename__ = "recommendation_logs"
    __table_args__ = (
        Index("ix_rec_log_user_created", "user_id", "created_at"),
        Index("ix_rec_log_job_id", "job_id"),
        {"schema": "jobseeker"}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False
    )
    job_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.jobs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Recommendation details
    base_score = Column(Float, nullable=False)  # Score before ML adjustments
    ml_adjustment = Column(Float, default=0.0, nullable=False)  # ML boost/penalty
    final_score = Column(Float, nullable=False)  # Final recommendation score
    rank_position = Column(Integer)  # Position in recommendation list

    # Score breakdown for analysis
    score_breakdown = Column(JSONB, nullable=False, default=dict)

    # Recommendation context
    recommendation_type = Column(String(50), default="personalized")  # personalized, similar, trending
    algorithm_version = Column(String(50), default="v1")

    # Outcome tracking (updated when user interacts)
    was_viewed = Column(Boolean, default=False)
    was_clicked = Column(Boolean, default=False)
    was_saved = Column(Boolean, default=False)
    was_applied = Column(Boolean, default=False)
    was_rejected = Column(Boolean, default=False)
    outcome_recorded_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    job = relationship("Job")

    @property
    def had_positive_outcome(self) -> bool:
        """Check if recommendation led to positive engagement."""
        return self.was_saved or self.was_applied

    @property
    def had_negative_outcome(self) -> bool:
        """Check if recommendation was rejected."""
        return self.was_rejected


class SimilarUserCluster(Base):
    """Store clusters of similar users for collaborative filtering."""

    __tablename__ = "similar_user_clusters"
    __table_args__ = {"schema": "jobseeker"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    cluster_id = Column(Integer, nullable=False, index=True)

    # Cluster characteristics (centroid features)
    cluster_features = Column(JSONB, nullable=False, default=dict)
    # Example: {"avg_skills": ["python", "aws"], "avg_experience": 5, "prefers_remote": 0.8}

    # Popular jobs in this cluster (stored as JSON array of UUID strings)
    popular_job_ids = Column(JSONB, nullable=False, default=list)

    # Cluster size
    member_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserClusterMembership(Base):
    """Track which cluster each user belongs to."""

    __tablename__ = "user_cluster_memberships"
    __table_args__ = (
        Index("ix_cluster_membership_user", "user_id"),
        Index("ix_cluster_membership_cluster", "cluster_id"),
        {"schema": "jobseeker"}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False
    )
    cluster_id = Column(Integer, nullable=False)

    # How well the user fits this cluster (0-1)
    membership_strength = Column(Float, default=1.0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
