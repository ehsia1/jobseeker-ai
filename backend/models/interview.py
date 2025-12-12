"""Interview coaching models for storing sessions and practice questions."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    ForeignKey,
    DateTime,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from backend.database import Base


class InterviewType(str, Enum):
    """Types of interview practice sessions."""

    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    CASE_STUDY = "case_study"
    SITUATIONAL = "situational"
    COMPETENCY = "competency"


class DifficultyLevel(str, Enum):
    """Difficulty levels for interview questions."""

    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class InterviewSession(Base):
    """Model for storing interview practice sessions."""

    __tablename__ = "interview_sessions"
    __table_args__ = (
        Index("ix_interview_sessions_user_id", "user_id"),
        Index("ix_interview_sessions_job_id", "job_id"),
        Index("ix_interview_sessions_created_at", "created_at"),
        {"schema": "jobseeker"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("jobseeker.jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Session configuration
    interview_type = Column(
        SQLEnum(InterviewType, name="interview_type_enum", schema="jobseeker"),
        nullable=False,
        default=InterviewType.BEHAVIORAL,
    )
    difficulty = Column(
        SQLEnum(DifficultyLevel, name="difficulty_level_enum", schema="jobseeker"),
        nullable=False,
        default=DifficultyLevel.MID,
    )
    target_role = Column(String(255), nullable=True)
    target_company = Column(String(255), nullable=True)
    focus_areas = Column(JSONB, nullable=True, default=list)  # List of focus topics

    # Session state
    total_questions = Column(Integer, default=5)
    completed_questions = Column(Integer, default=0)
    overall_score = Column(Integer, nullable=True)  # 0-100
    feedback_summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    job = relationship("Job", back_populates="interview_sessions")
    questions = relationship(
        "InterviewQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.question_order",
    )

    def __repr__(self) -> str:
        return f"<InterviewSession {self.id} type={self.interview_type.value}>"

    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.completed_at is not None

    @property
    def progress_percentage(self) -> int:
        """Calculate progress percentage."""
        if self.total_questions == 0:
            return 0
        return int((self.completed_questions / self.total_questions) * 100)


class InterviewQuestion(Base):
    """Model for storing individual interview questions and responses."""

    __tablename__ = "interview_questions"
    __table_args__ = (
        Index("ix_interview_questions_session_id", "session_id"),
        {"schema": "jobseeker"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("jobseeker.interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Question details
    question_order = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    question_category = Column(String(100), nullable=True)  # e.g., "leadership", "conflict"
    expected_framework = Column(String(50), nullable=True)  # e.g., "STAR", "CAR"

    # User response
    user_response = Column(Text, nullable=True)
    response_duration_seconds = Column(Integer, nullable=True)  # How long they took

    # AI feedback
    feedback = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)  # 0-100
    strengths = Column(JSONB, nullable=True, default=list)  # List of strengths
    improvements = Column(JSONB, nullable=True, default=list)  # List of areas to improve
    sample_answer = Column(Text, nullable=True)  # AI-generated ideal answer

    # Timestamps
    asked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    answered_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("InterviewSession", back_populates="questions")

    def __repr__(self) -> str:
        return f"<InterviewQuestion {self.id} order={self.question_order}>"

    @property
    def is_answered(self) -> bool:
        """Check if question has been answered."""
        return self.user_response is not None and self.answered_at is not None
