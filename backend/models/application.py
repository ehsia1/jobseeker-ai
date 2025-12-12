"""Application tracking models for job application lifecycle management."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class ApplicationStatus(str, Enum):
    """Application status values."""

    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    HIRED = "hired"


class ReminderType(str, Enum):
    """Types of application reminders."""

    FOLLOW_UP = "follow_up"
    INTERVIEW_PREP = "interview_prep"
    INTERVIEW = "interview"
    DEADLINE = "deadline"
    CUSTOM = "custom"


class ApplicationTimeline(Base):
    """Track application status changes over time for audit trail."""

    __tablename__ = "application_timeline"
    __table_args__ = (
        Index("ix_timeline_match_id", "job_match_id"),
        Index("ix_timeline_created", "created_at"),
        {"schema": "jobseeker"}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_match_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.job_matches.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Status tracking
    from_status = Column(String(50))  # Previous status (null for initial entry)
    to_status = Column(String(50), nullable=False)  # New status

    # Optional details
    notes = Column(Text)  # Notes about this status change
    extra_data = Column(Text)  # JSON string for additional data (interview date, etc.)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    job_match = relationship("JobMatch", back_populates="timeline_entries")
    user = relationship("User", back_populates="application_timeline")

    def __repr__(self) -> str:
        return f"<ApplicationTimeline {self.from_status} -> {self.to_status}>"


class ApplicationReminder(Base):
    """Reminders for application follow-ups and interviews."""

    __tablename__ = "application_reminders"
    __table_args__ = (
        Index("ix_reminder_user_scheduled", "user_id", "scheduled_for"),
        Index("ix_reminder_match_id", "job_match_id"),
        {"schema": "jobseeker"}
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_match_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.job_matches.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobseeker.users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Reminder details
    reminder_type = Column(String(50), nullable=False, default=ReminderType.FOLLOW_UP.value)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)

    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True))
    is_dismissed = Column(Boolean, default=False, nullable=False)

    # Notification tracking
    notification_sent = Column(Boolean, default=False, nullable=False)
    notification_sent_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    job_match = relationship("JobMatch", back_populates="reminders")
    user = relationship("User", back_populates="application_reminders")

    @property
    def is_overdue(self) -> bool:
        """Check if reminder is past due."""
        if self.is_completed or self.is_dismissed:
            return False
        return datetime.utcnow() > self.scheduled_for.replace(tzinfo=None)

    @property
    def is_upcoming(self) -> bool:
        """Check if reminder is upcoming (within 24 hours)."""
        if self.is_completed or self.is_dismissed:
            return False
        now = datetime.utcnow()
        scheduled = self.scheduled_for.replace(tzinfo=None)
        return now < scheduled and (scheduled - now).total_seconds() < 86400

    def __repr__(self) -> str:
        return f"<ApplicationReminder {self.title} @ {self.scheduled_for}>"
