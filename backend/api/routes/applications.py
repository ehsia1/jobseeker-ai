"""Application tracking routes for job application lifecycle management."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.models.application import ApplicationStatus, ReminderType
from backend.services.application_service import ApplicationTrackingService
from backend.api.schemas.application import (
    ApplicationStatusEnum,
    ReminderTypeEnum,
    UpdateStatusRequest,
    CreateReminderRequest,
    ScheduleInterviewRequest,
    TimelineEntryResponse,
    ReminderResponse,
    ReminderWithJobResponse,
    ApplicationTimelineResponse,
    ApplicationStatsResponse,
    ReminderListResponse,
    UpdateStatusResponse,
    UpcomingRemindersResponse,
    ApplicationDetailResponse,
    ApplicationHealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Optional OAuth2 scheme for demo mode compatibility
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user_or_demo(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user, or create/get demo user in demo mode."""
    # Demo mode: use demo user
    if settings.demo_mode and token is None:
        from uuid import uuid4

        # Get or create demo user
        result = await db.execute(
            select(User).where(User.email == "demo@localhost")
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid4(),
                email="demo@localhost",
                username="demo",
                password_hash="demo_not_used",
                is_active=True,
                is_premium=True,
            )
            db.add(user)
            await db.flush()

        return user

    # No token provided in non-demo mode
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    try:
        from jose import JWTError, jwt

        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Get user from database
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def _timeline_to_response(entry) -> TimelineEntryResponse:
    """Convert ApplicationTimeline model to response schema."""
    return TimelineEntryResponse(
        id=entry.id,
        job_match_id=entry.job_match_id,
        from_status=entry.from_status,
        to_status=entry.to_status,
        notes=entry.notes,
        extra_data=entry.extra_data,
        created_at=entry.created_at,
    )


def _reminder_to_response(reminder) -> ReminderResponse:
    """Convert ApplicationReminder model to response schema."""
    return ReminderResponse(
        id=reminder.id,
        job_match_id=reminder.job_match_id,
        reminder_type=reminder.reminder_type,
        title=reminder.title,
        description=reminder.description,
        scheduled_for=reminder.scheduled_for,
        is_completed=reminder.is_completed,
        completed_at=reminder.completed_at,
        is_dismissed=reminder.is_dismissed,
        notification_sent=reminder.notification_sent,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
    )


def _reminder_with_job_to_response(reminder) -> ReminderWithJobResponse:
    """Convert ApplicationReminder model to response with job info."""
    job_title = None
    company = None
    if reminder.job_match and reminder.job_match.job:
        job_title = reminder.job_match.job.title
        company = reminder.job_match.job.company

    return ReminderWithJobResponse(
        id=reminder.id,
        job_match_id=reminder.job_match_id,
        reminder_type=reminder.reminder_type,
        title=reminder.title,
        description=reminder.description,
        scheduled_for=reminder.scheduled_for,
        is_completed=reminder.is_completed,
        completed_at=reminder.completed_at,
        is_dismissed=reminder.is_dismissed,
        notification_sent=reminder.notification_sent,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        job_title=job_title,
        company=company,
    )


# ============ Status Management ============


@router.put("/matches/{match_id}/status", response_model=UpdateStatusResponse)
async def update_application_status(
    match_id: UUID,
    request: UpdateStatusRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a job application.

    Tracks the transition in the application timeline and validates
    that the status change is valid based on the current status.

    Valid transitions:
    - new -> viewed, saved, rejected, withdrawn
    - viewed -> saved, applied, rejected, withdrawn
    - saved -> applied, rejected, withdrawn
    - applied -> screening, interviewing, rejected, withdrawn
    - screening -> interviewing, rejected, withdrawn
    - interviewing -> offer_received, rejected, withdrawn
    - offer_received -> offer_accepted, offer_declined, withdrawn
    - offer_accepted -> hired, withdrawn
    """
    try:
        service = ApplicationTrackingService(db)
        new_status = ApplicationStatus(request.status.value)

        timeline_entry = await service.update_application_status(
            user_id=current_user.id,
            job_match_id=match_id,
            new_status=new_status,
            notes=request.notes,
            extra_data=request.extra_data,
        )

        await db.commit()

        return UpdateStatusResponse(
            timeline_entry=_timeline_to_response(timeline_entry),
            new_status=timeline_entry.to_status,
            message=f"Status updated to {timeline_entry.to_status}",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application status",
        )


@router.get("/matches/{match_id}/timeline", response_model=ApplicationTimelineResponse)
async def get_application_timeline(
    match_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get the full timeline of status changes for a job application."""
    try:
        service = ApplicationTrackingService(db)

        # Get timeline entries
        entries = await service.get_application_timeline(
            user_id=current_user.id,
            job_match_id=match_id,
        )

        # Get match to determine current status
        match = await service.get_match_with_timeline(
            user_id=current_user.id,
            job_match_id=match_id,
        )

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job match not found",
            )

        return ApplicationTimelineResponse(
            job_match_id=match_id,
            entries=[_timeline_to_response(e) for e in entries],
            current_status=match.status or "new",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application timeline",
        )


@router.get("/matches/{match_id}/detail", response_model=ApplicationDetailResponse)
async def get_application_detail(
    match_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed application view with timeline and reminders."""
    try:
        service = ApplicationTrackingService(db)

        match = await service.get_match_with_timeline(
            user_id=current_user.id,
            job_match_id=match_id,
        )

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job match not found",
            )

        return ApplicationDetailResponse(
            job_match_id=match.id,
            job_id=match.job_id,
            job_title=match.job.title if match.job else "Unknown",
            company=match.job.company if match.job else None,
            current_status=match.status or "new",
            score=float(match.score),
            applied_at=match.applied_at,
            created_at=match.created_at,
            updated_at=match.updated_at,
            timeline=[_timeline_to_response(e) for e in match.timeline_entries],
            reminders=[_reminder_to_response(r) for r in match.reminders],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get application detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application details",
        )


# ============ Reminders ============


@router.post("/matches/{match_id}/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    match_id: UUID,
    request: CreateReminderRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Create a reminder for a job application.

    Reminder types:
    - follow_up: General follow-up reminder
    - interview_prep: Reminder to prepare for interview
    - interview: Interview time reminder
    - deadline: Application deadline reminder
    - custom: Custom reminder type
    """
    try:
        service = ApplicationTrackingService(db)
        reminder_type = ReminderType(request.reminder_type.value)

        reminder = await service.create_reminder(
            user_id=current_user.id,
            job_match_id=match_id,
            title=request.title,
            scheduled_for=request.scheduled_for,
            reminder_type=reminder_type,
            description=request.description,
        )

        await db.commit()
        return _reminder_to_response(reminder)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create reminder: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reminder",
        )


@router.post("/matches/{match_id}/schedule-interview", response_model=list[ReminderResponse], status_code=status.HTTP_201_CREATED)
async def schedule_interview(
    match_id: UUID,
    request: ScheduleInterviewRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Schedule interview and create prep/interview reminders.

    Creates two reminders:
    1. Preparation reminder (default: 24 hours before)
    2. Interview reminder (1 hour before)
    """
    try:
        service = ApplicationTrackingService(db)

        reminders = await service.schedule_interview_reminder(
            user_id=current_user.id,
            job_match_id=match_id,
            interview_time=request.interview_time,
            prep_hours_before=request.prep_hours_before,
        )

        await db.commit()
        return [_reminder_to_response(r) for r in reminders]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to schedule interview: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule interview reminders",
        )


@router.get("/reminders", response_model=ReminderListResponse)
async def list_reminders(
    include_completed: bool = False,
    include_dismissed: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """List all reminders for the current user.

    Returns reminders ordered by scheduled date (earliest first).
    """
    try:
        service = ApplicationTrackingService(db)

        reminders = await service.get_user_reminders(
            user_id=current_user.id,
            include_completed=include_completed,
            include_dismissed=include_dismissed,
            limit=limit,
        )

        # Get overdue and upcoming counts
        overdue = await service.get_overdue_reminders(current_user.id)
        upcoming = await service.get_upcoming_reminders(current_user.id)

        return ReminderListResponse(
            reminders=[_reminder_with_job_to_response(r) for r in reminders],
            total=len(reminders),
            overdue_count=len(overdue),
            upcoming_count=len(upcoming),
        )

    except Exception as e:
        logger.error(f"Failed to list reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reminders",
        )


@router.get("/reminders/upcoming", response_model=UpcomingRemindersResponse)
async def get_upcoming_reminders(
    hours_ahead: int = 24,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get reminders scheduled within the next N hours."""
    try:
        service = ApplicationTrackingService(db)

        reminders = await service.get_upcoming_reminders(
            user_id=current_user.id,
            hours_ahead=hours_ahead,
        )

        return UpcomingRemindersResponse(
            reminders=[_reminder_with_job_to_response(r) for r in reminders],
            hours_window=hours_ahead,
        )

    except Exception as e:
        logger.error(f"Failed to get upcoming reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve upcoming reminders",
        )


@router.get("/reminders/overdue", response_model=list[ReminderWithJobResponse])
async def get_overdue_reminders(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get all overdue reminders for the current user."""
    try:
        service = ApplicationTrackingService(db)

        reminders = await service.get_overdue_reminders(current_user.id)
        return [_reminder_with_job_to_response(r) for r in reminders]

    except Exception as e:
        logger.error(f"Failed to get overdue reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve overdue reminders",
        )


@router.post("/reminders/{reminder_id}/complete", response_model=ReminderResponse)
async def complete_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Mark a reminder as completed."""
    try:
        service = ApplicationTrackingService(db)

        reminder = await service.complete_reminder(
            user_id=current_user.id,
            reminder_id=reminder_id,
        )

        await db.commit()
        await db.refresh(reminder)
        return _reminder_to_response(reminder)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to complete reminder: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete reminder",
        )


@router.post("/reminders/{reminder_id}/dismiss", response_model=ReminderResponse)
async def dismiss_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a reminder without marking it as completed."""
    try:
        service = ApplicationTrackingService(db)

        reminder = await service.dismiss_reminder(
            user_id=current_user.id,
            reminder_id=reminder_id,
        )

        await db.commit()
        await db.refresh(reminder)
        return _reminder_to_response(reminder)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to dismiss reminder: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dismiss reminder",
        )


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Delete a reminder."""
    try:
        service = ApplicationTrackingService(db)

        deleted = await service.delete_reminder(
            user_id=current_user.id,
            reminder_id=reminder_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found",
            )

        await db.commit()
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete reminder: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reminder",
        )


# ============ Statistics ============


@router.get("/stats", response_model=ApplicationStatsResponse)
async def get_application_stats(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get application statistics for the current user.

    Returns aggregated data including:
    - Total applications
    - Active applications (applied, screening, interviewing, offer received)
    - Interview count
    - Offers received
    - Applications broken down by status
    - Recent activity count (last 7 days)
    """
    try:
        service = ApplicationTrackingService(db)
        stats = await service.get_application_stats(current_user.id)

        return ApplicationStatsResponse(
            total_applications=stats.total_applications,
            active_applications=stats.active_applications,
            interviews_scheduled=stats.interviews_scheduled,
            offers_received=stats.offers_received,
            applications_by_status=stats.applications_by_status,
            recent_activity_count=stats.recent_activity_count,
        )

    except Exception as e:
        logger.error(f"Failed to get application stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application statistics",
        )


# ============ Health Check ============


@router.get("/health", response_model=ApplicationHealthResponse)
async def application_health():
    """Check if the application tracking service is operational."""
    return ApplicationHealthResponse(
        status="healthy",
        supported_statuses=[s.value for s in ApplicationStatusEnum],
        supported_reminder_types=[r.value for r in ReminderTypeEnum],
    )
