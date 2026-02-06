"""Application Tracking Service - Manage job application lifecycle and reminders."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from backend.models.application import (
    ApplicationTimeline,
    ApplicationReminder,
    ApplicationStatus,
    ReminderType,
)
from backend.models.job import JobMatch, Job

logger = logging.getLogger(__name__)


@dataclass
class ApplicationStats:
    """Statistics for a user's job applications."""

    total_applications: int = 0
    active_applications: int = 0
    interviews_scheduled: int = 0
    offers_received: int = 0
    applications_by_status: Dict[str, int] = field(default_factory=dict)
    recent_activity_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_applications": self.total_applications,
            "active_applications": self.active_applications,
            "interviews_scheduled": self.interviews_scheduled,
            "offers_received": self.offers_received,
            "applications_by_status": self.applications_by_status,
            "recent_activity_count": self.recent_activity_count,
        }


class ApplicationTrackingService:
    """Service for tracking job application lifecycle and managing reminders."""

    # Status transitions that are valid
    VALID_TRANSITIONS = {
        ApplicationStatus.NEW: [
            ApplicationStatus.VIEWED,
            ApplicationStatus.SAVED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.VIEWED: [
            ApplicationStatus.SAVED,
            ApplicationStatus.APPLIED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.SAVED: [
            ApplicationStatus.APPLIED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.APPLIED: [
            ApplicationStatus.SCREENING,
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.SCREENING: [
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.INTERVIEWING: [
            ApplicationStatus.OFFER_RECEIVED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.OFFER_RECEIVED: [
            ApplicationStatus.OFFER_ACCEPTED,
            ApplicationStatus.OFFER_DECLINED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.OFFER_ACCEPTED: [
            ApplicationStatus.HIRED,
            ApplicationStatus.WITHDRAWN,
        ],
        ApplicationStatus.OFFER_DECLINED: [],
        ApplicationStatus.REJECTED: [],
        ApplicationStatus.WITHDRAWN: [],
        ApplicationStatus.HIRED: [],
    }

    def __init__(self, db: AsyncSession):
        """Initialize application tracking service.

        Args:
            db: Database session.
        """
        self.db = db

    async def update_application_status(
        self,
        user_id: UUID,
        job_match_id: UUID,
        new_status: ApplicationStatus,
        notes: Optional[str] = None,
        extra_data: Optional[str] = None,
    ) -> ApplicationTimeline:
        """Update application status and create timeline entry.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.
            new_status: New application status.
            notes: Optional notes about this status change.
            extra_data: Optional JSON string with additional data.

        Returns:
            Created ApplicationTimeline entry.

        Raises:
            ValueError: If transition is invalid or job match not found.
        """
        # Get the job match
        result = await self.db.execute(
            select(JobMatch)
            .where(and_(JobMatch.id == job_match_id, JobMatch.user_id == user_id))
        )
        job_match = result.scalar_one_or_none()

        if not job_match:
            raise ValueError("Job match not found")

        # Get current status
        current_status = ApplicationStatus(job_match.status) if job_match.status else ApplicationStatus.NEW

        # Validate transition
        valid_next = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next and current_status != new_status:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            )

        # Create timeline entry
        timeline_entry = ApplicationTimeline(
            job_match_id=job_match_id,
            user_id=user_id,
            from_status=current_status.value,
            to_status=new_status.value,
            notes=notes,
            extra_data=extra_data,
        )
        self.db.add(timeline_entry)

        # Update job match status
        job_match.status = new_status.value

        # Update applied_at if transitioning to APPLIED
        if new_status == ApplicationStatus.APPLIED and not job_match.applied_at:
            job_match.applied_at = datetime.utcnow()

        await self.db.flush()

        # Auto-create follow-up reminder when marking as applied
        if new_status == ApplicationStatus.APPLIED:
            try:
                await self._create_auto_follow_up(user_id, job_match_id, job_match)
            except Exception as e:
                # Don't fail the status update if reminder creation fails
                logger.warning(f"Failed to create auto follow-up reminder: {e}")

        logger.info(
            f"Updated application status for match {job_match_id}: "
            f"{current_status.value} -> {new_status.value}"
        )

        return timeline_entry

    async def _create_auto_follow_up(
        self,
        user_id: UUID,
        job_match_id: UUID,
        job_match: JobMatch,
    ) -> Optional[ApplicationReminder]:
        """Create automatic follow-up reminder when job is marked as applied.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.
            job_match: The job match object (for job title).

        Returns:
            Created reminder or None if skipped.
        """
        # Check if a follow-up reminder already exists for this match
        result = await self.db.execute(
            select(ApplicationReminder)
            .where(
                and_(
                    ApplicationReminder.job_match_id == job_match_id,
                    ApplicationReminder.user_id == user_id,
                    ApplicationReminder.reminder_type == ReminderType.FOLLOW_UP.value,
                    ApplicationReminder.is_completed == False,
                    ApplicationReminder.is_dismissed == False,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Follow-up reminder already exists for match {job_match_id}")
            return None

        # Get job title for the reminder
        job_title = "this position"
        if job_match.job:
            job_title = job_match.job.title
        elif hasattr(job_match, 'job_id'):
            # Try to load job
            job_result = await self.db.execute(
                select(Job).where(Job.id == job_match.job_id)
            )
            job = job_result.scalar_one_or_none()
            if job:
                job_title = job.title

        # Create follow-up reminder for 7 days from now
        scheduled_for = datetime.utcnow() + timedelta(days=7)

        reminder = ApplicationReminder(
            job_match_id=job_match_id,
            user_id=user_id,
            reminder_type=ReminderType.FOLLOW_UP.value,
            title=f"Follow up: {job_title[:50]}",
            description="No response yet? Consider sending a polite follow-up email to check on your application status.",
            scheduled_for=scheduled_for,
        )
        self.db.add(reminder)
        await self.db.flush()

        logger.info(f"Created auto follow-up reminder for match {job_match_id}, due {scheduled_for}")
        return reminder

    async def get_application_timeline(
        self,
        user_id: UUID,
        job_match_id: UUID,
    ) -> List[ApplicationTimeline]:
        """Get timeline entries for a job application.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.

        Returns:
            List of timeline entries, ordered by creation date.
        """
        result = await self.db.execute(
            select(ApplicationTimeline)
            .where(
                and_(
                    ApplicationTimeline.job_match_id == job_match_id,
                    ApplicationTimeline.user_id == user_id,
                )
            )
            .order_by(ApplicationTimeline.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_reminder(
        self,
        user_id: UUID,
        job_match_id: UUID,
        title: str,
        scheduled_for: datetime,
        reminder_type: ReminderType = ReminderType.FOLLOW_UP,
        description: Optional[str] = None,
    ) -> ApplicationReminder:
        """Create a reminder for a job application.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.
            title: Reminder title.
            scheduled_for: When to trigger the reminder.
            reminder_type: Type of reminder.
            description: Optional detailed description.

        Returns:
            Created ApplicationReminder.

        Raises:
            ValueError: If job match not found.
        """
        # Verify job match exists and belongs to user
        result = await self.db.execute(
            select(JobMatch)
            .where(and_(JobMatch.id == job_match_id, JobMatch.user_id == user_id))
        )
        job_match = result.scalar_one_or_none()

        if not job_match:
            raise ValueError("Job match not found")

        reminder = ApplicationReminder(
            job_match_id=job_match_id,
            user_id=user_id,
            reminder_type=reminder_type.value,
            title=title,
            description=description,
            scheduled_for=scheduled_for,
        )
        self.db.add(reminder)
        await self.db.flush()

        logger.info(f"Created reminder '{title}' for match {job_match_id}")
        return reminder

    async def get_reminder(self, reminder_id: UUID) -> Optional[ApplicationReminder]:
        """Get a reminder by ID.

        Args:
            reminder_id: Reminder UUID.

        Returns:
            ApplicationReminder if found, None otherwise.
        """
        result = await self.db.execute(
            select(ApplicationReminder)
            .where(ApplicationReminder.id == reminder_id)
            .options(selectinload(ApplicationReminder.job_match))
        )
        return result.scalar_one_or_none()

    async def get_user_reminders(
        self,
        user_id: UUID,
        include_completed: bool = False,
        include_dismissed: bool = False,
        limit: int = 50,
    ) -> List[ApplicationReminder]:
        """Get reminders for a user.

        Args:
            user_id: User ID.
            include_completed: Whether to include completed reminders.
            include_dismissed: Whether to include dismissed reminders.
            limit: Maximum number of reminders to return.

        Returns:
            List of reminders, ordered by scheduled date.
        """
        query = (
            select(ApplicationReminder)
            .where(ApplicationReminder.user_id == user_id)
            .options(selectinload(ApplicationReminder.job_match))
            .order_by(ApplicationReminder.scheduled_for.asc())
            .limit(limit)
        )

        if not include_completed:
            query = query.where(ApplicationReminder.is_completed == False)

        if not include_dismissed:
            query = query.where(ApplicationReminder.is_dismissed == False)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_reminders(
        self,
        user_id: UUID,
        hours_ahead: int = 24,
    ) -> List[ApplicationReminder]:
        """Get upcoming reminders within a time window.

        Args:
            user_id: User ID.
            hours_ahead: Number of hours to look ahead.

        Returns:
            List of upcoming reminders.
        """
        now = datetime.utcnow()
        future = now + timedelta(hours=hours_ahead)

        result = await self.db.execute(
            select(ApplicationReminder)
            .where(
                and_(
                    ApplicationReminder.user_id == user_id,
                    ApplicationReminder.is_completed == False,
                    ApplicationReminder.is_dismissed == False,
                    ApplicationReminder.scheduled_for >= now,
                    ApplicationReminder.scheduled_for <= future,
                )
            )
            .options(selectinload(ApplicationReminder.job_match))
            .order_by(ApplicationReminder.scheduled_for.asc())
        )
        return list(result.scalars().all())

    async def get_overdue_reminders(self, user_id: UUID) -> List[ApplicationReminder]:
        """Get overdue reminders for a user.

        Args:
            user_id: User ID.

        Returns:
            List of overdue reminders.
        """
        now = datetime.utcnow()

        result = await self.db.execute(
            select(ApplicationReminder)
            .where(
                and_(
                    ApplicationReminder.user_id == user_id,
                    ApplicationReminder.is_completed == False,
                    ApplicationReminder.is_dismissed == False,
                    ApplicationReminder.scheduled_for < now,
                )
            )
            .options(selectinload(ApplicationReminder.job_match))
            .order_by(ApplicationReminder.scheduled_for.asc())
        )
        return list(result.scalars().all())

    async def complete_reminder(
        self,
        user_id: UUID,
        reminder_id: UUID,
    ) -> ApplicationReminder:
        """Mark a reminder as completed.

        Args:
            user_id: User ID.
            reminder_id: Reminder ID.

        Returns:
            Updated ApplicationReminder.

        Raises:
            ValueError: If reminder not found.
        """
        result = await self.db.execute(
            select(ApplicationReminder)
            .where(
                and_(
                    ApplicationReminder.id == reminder_id,
                    ApplicationReminder.user_id == user_id,
                )
            )
        )
        reminder = result.scalar_one_or_none()

        if not reminder:
            raise ValueError("Reminder not found")

        reminder.is_completed = True
        reminder.completed_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"Completed reminder {reminder_id}")
        return reminder

    async def dismiss_reminder(
        self,
        user_id: UUID,
        reminder_id: UUID,
    ) -> ApplicationReminder:
        """Dismiss a reminder without completing it.

        Args:
            user_id: User ID.
            reminder_id: Reminder ID.

        Returns:
            Updated ApplicationReminder.

        Raises:
            ValueError: If reminder not found.
        """
        result = await self.db.execute(
            select(ApplicationReminder)
            .where(
                and_(
                    ApplicationReminder.id == reminder_id,
                    ApplicationReminder.user_id == user_id,
                )
            )
        )
        reminder = result.scalar_one_or_none()

        if not reminder:
            raise ValueError("Reminder not found")

        reminder.is_dismissed = True
        await self.db.flush()

        logger.info(f"Dismissed reminder {reminder_id}")
        return reminder

    async def delete_reminder(
        self,
        user_id: UUID,
        reminder_id: UUID,
    ) -> bool:
        """Delete a reminder.

        Args:
            user_id: User ID.
            reminder_id: Reminder ID.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.db.execute(
            select(ApplicationReminder)
            .where(
                and_(
                    ApplicationReminder.id == reminder_id,
                    ApplicationReminder.user_id == user_id,
                )
            )
        )
        reminder = result.scalar_one_or_none()

        if not reminder:
            return False

        await self.db.delete(reminder)
        await self.db.flush()

        logger.info(f"Deleted reminder {reminder_id}")
        return True

    async def get_application_stats(self, user_id: UUID) -> ApplicationStats:
        """Get application statistics for a user.

        Args:
            user_id: User ID.

        Returns:
            ApplicationStats with aggregated data.
        """
        # Get all job matches for the user
        result = await self.db.execute(
            select(JobMatch)
            .where(JobMatch.user_id == user_id)
        )
        matches = list(result.scalars().all())

        # Calculate statistics
        stats = ApplicationStats()
        stats.total_applications = len(matches)

        # Count by status
        active_statuses = [
            ApplicationStatus.APPLIED.value,
            ApplicationStatus.SCREENING.value,
            ApplicationStatus.INTERVIEWING.value,
            ApplicationStatus.OFFER_RECEIVED.value,
        ]

        for match in matches:
            status = match.status or ApplicationStatus.NEW.value
            stats.applications_by_status[status] = (
                stats.applications_by_status.get(status, 0) + 1
            )

            if status in active_statuses:
                stats.active_applications += 1

            if status == ApplicationStatus.INTERVIEWING.value:
                stats.interviews_scheduled += 1

            if status in [
                ApplicationStatus.OFFER_RECEIVED.value,
                ApplicationStatus.OFFER_ACCEPTED.value,
            ]:
                stats.offers_received += 1

        # Count recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        timeline_result = await self.db.execute(
            select(ApplicationTimeline)
            .where(
                and_(
                    ApplicationTimeline.user_id == user_id,
                    ApplicationTimeline.created_at >= week_ago,
                )
            )
        )
        stats.recent_activity_count = len(list(timeline_result.scalars().all()))

        return stats

    async def get_match_with_timeline(
        self,
        user_id: UUID,
        job_match_id: UUID,
    ) -> Optional[JobMatch]:
        """Get a job match with its full timeline.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.

        Returns:
            JobMatch with timeline and reminders loaded, or None.
        """
        result = await self.db.execute(
            select(JobMatch)
            .where(and_(JobMatch.id == job_match_id, JobMatch.user_id == user_id))
            .options(
                selectinload(JobMatch.timeline_entries),
                selectinload(JobMatch.reminders),
                selectinload(JobMatch.job),
            )
        )
        return result.scalar_one_or_none()

    async def create_follow_up_reminder(
        self,
        user_id: UUID,
        job_match_id: UUID,
        days_from_now: int = 7,
    ) -> ApplicationReminder:
        """Create a follow-up reminder for a job application.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.
            days_from_now: Days until the reminder.

        Returns:
            Created ApplicationReminder.
        """
        scheduled_for = datetime.utcnow() + timedelta(days=days_from_now)

        return await self.create_reminder(
            user_id=user_id,
            job_match_id=job_match_id,
            title="Follow up on application",
            scheduled_for=scheduled_for,
            reminder_type=ReminderType.FOLLOW_UP,
            description="Time to follow up on this job application.",
        )

    async def schedule_interview_reminder(
        self,
        user_id: UUID,
        job_match_id: UUID,
        interview_time: datetime,
        prep_hours_before: int = 24,
    ) -> List[ApplicationReminder]:
        """Schedule interview and preparation reminders.

        Args:
            user_id: User ID.
            job_match_id: Job match ID.
            interview_time: When the interview is scheduled.
            prep_hours_before: Hours before interview for prep reminder.

        Returns:
            List of created reminders (prep + interview).
        """
        reminders = []

        # Prep reminder
        prep_time = interview_time - timedelta(hours=prep_hours_before)
        prep_reminder = await self.create_reminder(
            user_id=user_id,
            job_match_id=job_match_id,
            title="Interview preparation time",
            scheduled_for=prep_time,
            reminder_type=ReminderType.INTERVIEW_PREP,
            description="Start preparing for your upcoming interview!",
        )
        reminders.append(prep_reminder)

        # Interview reminder (1 hour before)
        interview_reminder_time = interview_time - timedelta(hours=1)
        interview_reminder = await self.create_reminder(
            user_id=user_id,
            job_match_id=job_match_id,
            title="Interview in 1 hour",
            scheduled_for=interview_reminder_time,
            reminder_type=ReminderType.INTERVIEW,
            description="Your interview is in 1 hour. Good luck!",
        )
        reminders.append(interview_reminder)

        return reminders


# Convenience functions
async def update_application_status(
    db: AsyncSession,
    user_id: UUID,
    job_match_id: UUID,
    new_status: ApplicationStatus,
    **kwargs,
) -> ApplicationTimeline:
    """Update application status."""
    service = ApplicationTrackingService(db)
    return await service.update_application_status(
        user_id, job_match_id, new_status, **kwargs
    )


async def create_reminder(
    db: AsyncSession,
    user_id: UUID,
    job_match_id: UUID,
    title: str,
    scheduled_for: datetime,
    **kwargs,
) -> ApplicationReminder:
    """Create a reminder."""
    service = ApplicationTrackingService(db)
    return await service.create_reminder(
        user_id, job_match_id, title, scheduled_for, **kwargs
    )
