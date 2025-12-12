"""Application tracking Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class ApplicationStatusEnum(str, Enum):
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


class ReminderTypeEnum(str, Enum):
    """Types of application reminders."""

    FOLLOW_UP = "follow_up"
    INTERVIEW_PREP = "interview_prep"
    INTERVIEW = "interview"
    DEADLINE = "deadline"
    CUSTOM = "custom"


# Request schemas
class UpdateStatusRequest(BaseModel):
    """Request to update application status."""

    status: ApplicationStatusEnum = Field(
        ...,
        description="New application status",
    )
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Notes about this status change",
    )
    extra_data: Optional[str] = Field(
        None,
        max_length=5000,
        description="JSON string with additional data",
    )


class CreateReminderRequest(BaseModel):
    """Request to create a reminder."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Reminder title",
    )
    scheduled_for: datetime = Field(
        ...,
        description="When to trigger the reminder",
    )
    reminder_type: ReminderTypeEnum = Field(
        default=ReminderTypeEnum.FOLLOW_UP,
        description="Type of reminder",
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed description",
    )


class ScheduleInterviewRequest(BaseModel):
    """Request to schedule interview reminders."""

    interview_time: datetime = Field(
        ...,
        description="When the interview is scheduled",
    )
    prep_hours_before: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours before interview for prep reminder",
    )


# Response schemas
class TimelineEntryResponse(BaseModel):
    """Response schema for a timeline entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_match_id: UUID
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None
    extra_data: Optional[str] = None
    created_at: datetime


class ReminderResponse(BaseModel):
    """Response schema for a reminder."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_match_id: UUID
    reminder_type: str
    title: str
    description: Optional[str] = None
    scheduled_for: datetime
    is_completed: bool
    completed_at: Optional[datetime] = None
    is_dismissed: bool
    notification_sent: bool
    created_at: datetime
    updated_at: datetime

    @property
    def is_overdue(self) -> bool:
        """Check if reminder is past due."""
        if self.is_completed or self.is_dismissed:
            return False
        return datetime.utcnow() > self.scheduled_for.replace(tzinfo=None)


class ReminderWithJobResponse(ReminderResponse):
    """Reminder response with job information."""

    job_title: Optional[str] = None
    company: Optional[str] = None


class ApplicationTimelineResponse(BaseModel):
    """Response schema for application timeline."""

    job_match_id: UUID
    entries: List[TimelineEntryResponse]
    current_status: str


class ApplicationStatsResponse(BaseModel):
    """Response schema for application statistics."""

    total_applications: int
    active_applications: int
    interviews_scheduled: int
    offers_received: int
    applications_by_status: Dict[str, int]
    recent_activity_count: int


class ReminderListResponse(BaseModel):
    """Response for listing reminders."""

    reminders: List[ReminderWithJobResponse]
    total: int
    overdue_count: int
    upcoming_count: int


class UpdateStatusResponse(BaseModel):
    """Response after updating status."""

    timeline_entry: TimelineEntryResponse
    new_status: str
    message: str


class UpcomingRemindersResponse(BaseModel):
    """Response for upcoming reminders."""

    reminders: List[ReminderWithJobResponse]
    hours_window: int


class ApplicationDetailResponse(BaseModel):
    """Detailed application view with timeline and reminders."""

    model_config = ConfigDict(from_attributes=True)

    job_match_id: UUID
    job_id: UUID
    job_title: str
    company: Optional[str] = None
    current_status: str
    score: float
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    timeline: List[TimelineEntryResponse]
    reminders: List[ReminderResponse]


class ApplicationHealthResponse(BaseModel):
    """Health check response for application tracking service."""

    status: str
    supported_statuses: List[str]
    supported_reminder_types: List[str]
