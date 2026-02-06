"""
Unit tests for the ApplicationTrackingService.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from backend.services.application_service import (
    ApplicationTrackingService,
    ApplicationStats,
)
from backend.models.application import (
    ApplicationTimeline,
    ApplicationReminder,
    ApplicationStatus,
    ReminderType,
)
from backend.models.job import JobMatch


class TestApplicationStats:
    """Tests for ApplicationStats dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = ApplicationStats(
            total_applications=10,
            active_applications=5,
            interviews_scheduled=2,
            offers_received=1,
            applications_by_status={"applied": 5, "interviewing": 2, "new": 3},
            recent_activity_count=15,
        )

        result = stats.to_dict()

        assert result["total_applications"] == 10
        assert result["active_applications"] == 5
        assert result["interviews_scheduled"] == 2
        assert result["offers_received"] == 1
        assert result["applications_by_status"]["applied"] == 5
        assert result["recent_activity_count"] == 15

    def test_to_dict_with_defaults(self):
        """Test conversion with default values."""
        stats = ApplicationStats()

        result = stats.to_dict()

        assert result["total_applications"] == 0
        assert result["active_applications"] == 0
        assert result["interviews_scheduled"] == 0
        assert result["offers_received"] == 0
        assert result["applications_by_status"] == {}
        assert result["recent_activity_count"] == 0


class TestApplicationStatus:
    """Tests for ApplicationStatus enum."""

    def test_application_status_values(self):
        """Test application status enum values."""
        assert ApplicationStatus.NEW.value == "new"
        assert ApplicationStatus.VIEWED.value == "viewed"
        assert ApplicationStatus.SAVED.value == "saved"
        assert ApplicationStatus.APPLIED.value == "applied"
        assert ApplicationStatus.SCREENING.value == "screening"
        assert ApplicationStatus.INTERVIEWING.value == "interviewing"
        assert ApplicationStatus.OFFER_RECEIVED.value == "offer_received"
        assert ApplicationStatus.OFFER_ACCEPTED.value == "offer_accepted"
        assert ApplicationStatus.OFFER_DECLINED.value == "offer_declined"
        assert ApplicationStatus.REJECTED.value == "rejected"
        assert ApplicationStatus.WITHDRAWN.value == "withdrawn"
        assert ApplicationStatus.HIRED.value == "hired"

    def test_application_status_from_string(self):
        """Test creating application status from string."""
        assert ApplicationStatus("new") == ApplicationStatus.NEW
        assert ApplicationStatus("applied") == ApplicationStatus.APPLIED
        assert ApplicationStatus("interviewing") == ApplicationStatus.INTERVIEWING


class TestReminderType:
    """Tests for ReminderType enum."""

    def test_reminder_type_values(self):
        """Test reminder type enum values."""
        assert ReminderType.FOLLOW_UP.value == "follow_up"
        assert ReminderType.INTERVIEW_PREP.value == "interview_prep"
        assert ReminderType.INTERVIEW.value == "interview"
        assert ReminderType.DEADLINE.value == "deadline"
        assert ReminderType.CUSTOM.value == "custom"


class TestValidTransitions:
    """Tests for application status transition validation."""

    def test_valid_transitions_from_new(self):
        """Test valid transitions from NEW status."""
        valid_from_new = ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.NEW]
        assert ApplicationStatus.VIEWED in valid_from_new
        assert ApplicationStatus.SAVED in valid_from_new
        assert ApplicationStatus.REJECTED in valid_from_new
        assert ApplicationStatus.WITHDRAWN in valid_from_new
        # Should NOT be able to go directly to APPLIED from NEW
        assert ApplicationStatus.APPLIED not in valid_from_new

    def test_valid_transitions_from_viewed(self):
        """Test valid transitions from VIEWED status."""
        valid_from_viewed = ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.VIEWED]
        assert ApplicationStatus.SAVED in valid_from_viewed
        assert ApplicationStatus.APPLIED in valid_from_viewed
        assert ApplicationStatus.REJECTED in valid_from_viewed
        assert ApplicationStatus.WITHDRAWN in valid_from_viewed

    def test_valid_transitions_from_applied(self):
        """Test valid transitions from APPLIED status."""
        valid_from_applied = ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.APPLIED]
        assert ApplicationStatus.SCREENING in valid_from_applied
        assert ApplicationStatus.INTERVIEWING in valid_from_applied
        assert ApplicationStatus.REJECTED in valid_from_applied
        assert ApplicationStatus.WITHDRAWN in valid_from_applied

    def test_valid_transitions_from_interviewing(self):
        """Test valid transitions from INTERVIEWING status."""
        valid_from_interviewing = ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.INTERVIEWING]
        assert ApplicationStatus.OFFER_RECEIVED in valid_from_interviewing
        assert ApplicationStatus.REJECTED in valid_from_interviewing
        assert ApplicationStatus.WITHDRAWN in valid_from_interviewing

    def test_valid_transitions_from_offer_received(self):
        """Test valid transitions from OFFER_RECEIVED status."""
        valid_from_offer = ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.OFFER_RECEIVED]
        assert ApplicationStatus.OFFER_ACCEPTED in valid_from_offer
        assert ApplicationStatus.OFFER_DECLINED in valid_from_offer
        assert ApplicationStatus.WITHDRAWN in valid_from_offer

    def test_terminal_states_have_no_transitions(self):
        """Test that terminal states have no valid transitions."""
        assert ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.OFFER_DECLINED] == []
        assert ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.REJECTED] == []
        assert ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.WITHDRAWN] == []
        assert ApplicationTrackingService.VALID_TRANSITIONS[ApplicationStatus.HIRED] == []


class TestApplicationTrackingService:
    """Tests for ApplicationTrackingService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.delete = AsyncMock()
        mock.flush = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return ApplicationTrackingService(mock_db)

    @pytest.fixture
    def mock_job_match(self):
        """Create mock job match."""
        match = MagicMock(spec=JobMatch)
        match.id = uuid4()
        match.user_id = uuid4()
        match.job_id = uuid4()
        match.status = "new"
        match.applied_at = None
        return match

    @pytest.mark.asyncio
    async def test_update_application_status_success(self, service, mock_db, mock_job_match):
        """Test successful status update."""
        user_id = mock_job_match.user_id
        job_match_id = mock_job_match.id

        # Mock execute to return the job match
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match
        mock_db.execute.return_value = mock_result

        result = await service.update_application_status(
            user_id=user_id,
            job_match_id=job_match_id,
            new_status=ApplicationStatus.VIEWED,
            notes="Reviewed the job posting",
        )

        # Verify timeline entry was added
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

        # Verify job match status was updated
        assert mock_job_match.status == ApplicationStatus.VIEWED.value

    @pytest.mark.asyncio
    async def test_update_application_status_to_applied_sets_applied_at(
        self, service, mock_db, mock_job_match
    ):
        """Test that transitioning to APPLIED sets applied_at timestamp."""
        user_id = mock_job_match.user_id
        job_match_id = mock_job_match.id
        mock_job_match.status = "viewed"  # Must be viewed before applied

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match
        mock_db.execute.return_value = mock_result

        await service.update_application_status(
            user_id=user_id,
            job_match_id=job_match_id,
            new_status=ApplicationStatus.APPLIED,
        )

        assert mock_job_match.applied_at is not None

    @pytest.mark.asyncio
    async def test_update_application_status_job_match_not_found(
        self, service, mock_db
    ):
        """Test error when job match not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Job match not found"):
            await service.update_application_status(
                user_id=uuid4(),
                job_match_id=uuid4(),
                new_status=ApplicationStatus.VIEWED,
            )

    @pytest.mark.asyncio
    async def test_update_application_status_invalid_transition(
        self, service, mock_db, mock_job_match
    ):
        """Test error on invalid status transition."""
        mock_job_match.status = "hired"  # Terminal state

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Invalid status transition"):
            await service.update_application_status(
                user_id=mock_job_match.user_id,
                job_match_id=mock_job_match.id,
                new_status=ApplicationStatus.APPLIED,
            )

    @pytest.mark.asyncio
    async def test_create_reminder_success(self, service, mock_db, mock_job_match):
        """Test successful reminder creation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match
        mock_db.execute.return_value = mock_result

        scheduled_for = datetime.utcnow() + timedelta(days=7)

        result = await service.create_reminder(
            user_id=mock_job_match.user_id,
            job_match_id=mock_job_match.id,
            title="Follow up reminder",
            scheduled_for=scheduled_for,
            reminder_type=ReminderType.FOLLOW_UP,
            description="Remember to follow up on this application",
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_reminder_job_match_not_found(self, service, mock_db):
        """Test error when creating reminder for non-existent job match."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Job match not found"):
            await service.create_reminder(
                user_id=uuid4(),
                job_match_id=uuid4(),
                title="Test reminder",
                scheduled_for=datetime.utcnow() + timedelta(days=1),
            )

    @pytest.mark.asyncio
    async def test_complete_reminder_success(self, service, mock_db):
        """Test successfully completing a reminder."""
        reminder = MagicMock(spec=ApplicationReminder)
        reminder.id = uuid4()
        reminder.user_id = uuid4()
        reminder.is_completed = False
        reminder.completed_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = reminder
        mock_db.execute.return_value = mock_result

        result = await service.complete_reminder(
            user_id=reminder.user_id,
            reminder_id=reminder.id,
        )

        assert reminder.is_completed == True
        assert reminder.completed_at is not None
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_reminder_not_found(self, service, mock_db):
        """Test error when completing non-existent reminder."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Reminder not found"):
            await service.complete_reminder(
                user_id=uuid4(),
                reminder_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_dismiss_reminder_success(self, service, mock_db):
        """Test successfully dismissing a reminder."""
        reminder = MagicMock(spec=ApplicationReminder)
        reminder.id = uuid4()
        reminder.user_id = uuid4()
        reminder.is_dismissed = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = reminder
        mock_db.execute.return_value = mock_result

        result = await service.dismiss_reminder(
            user_id=reminder.user_id,
            reminder_id=reminder.id,
        )

        assert reminder.is_dismissed == True
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_reminder_not_found(self, service, mock_db):
        """Test error when dismissing non-existent reminder."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Reminder not found"):
            await service.dismiss_reminder(
                user_id=uuid4(),
                reminder_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_delete_reminder_success(self, service, mock_db):
        """Test successfully deleting a reminder."""
        reminder = MagicMock(spec=ApplicationReminder)
        reminder.id = uuid4()
        reminder.user_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = reminder
        mock_db.execute.return_value = mock_result

        result = await service.delete_reminder(
            user_id=reminder.user_id,
            reminder_id=reminder.id,
        )

        assert result == True
        mock_db.delete.assert_called_once_with(reminder)
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_reminder_not_found(self, service, mock_db):
        """Test delete returns False when reminder not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.delete_reminder(
            user_id=uuid4(),
            reminder_id=uuid4(),
        )

        assert result == False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_follow_up_reminder(self, service, mock_db, mock_job_match):
        """Test creating a follow-up reminder with default timing."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match
        mock_db.execute.return_value = mock_result

        result = await service.create_follow_up_reminder(
            user_id=mock_job_match.user_id,
            job_match_id=mock_job_match.id,
            days_from_now=7,
        )

        # Verify reminder was created
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_interview_reminder_creates_two_reminders(
        self, service, mock_db, mock_job_match
    ):
        """Test that scheduling interview creates prep and interview reminders."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match
        mock_db.execute.return_value = mock_result

        interview_time = datetime.utcnow() + timedelta(days=3)

        result = await service.schedule_interview_reminder(
            user_id=mock_job_match.user_id,
            job_match_id=mock_job_match.id,
            interview_time=interview_time,
            prep_hours_before=24,
        )

        # Should create 2 reminders (prep + interview)
        assert mock_db.add.call_count == 2
        assert len(result) == 2


class TestApplicationStatsCalculation:
    """Tests for application statistics calculation."""

    @pytest.mark.asyncio
    async def test_get_application_stats_empty(self):
        """Test stats calculation with no applications."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # Return empty matches
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        service = ApplicationTrackingService(mock_db)
        stats = await service.get_application_stats(uuid4())

        assert stats.total_applications == 0
        assert stats.active_applications == 0
        assert stats.interviews_scheduled == 0
        assert stats.offers_received == 0

    @pytest.mark.asyncio
    async def test_get_application_stats_with_applications(self):
        """Test stats calculation with various application statuses."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # Create mock matches with different statuses
        matches = [
            MagicMock(status="applied"),
            MagicMock(status="applied"),
            MagicMock(status="screening"),
            MagicMock(status="interviewing"),
            MagicMock(status="interviewing"),
            MagicMock(status="offer_received"),
            MagicMock(status="rejected"),
            MagicMock(status="new"),
        ]

        # First call returns matches, second call returns timeline entries
        mock_result1 = MagicMock()
        mock_scalars1 = MagicMock()
        mock_scalars1.all.return_value = matches
        mock_result1.scalars.return_value = mock_scalars1

        mock_result2 = MagicMock()
        mock_scalars2 = MagicMock()
        mock_scalars2.all.return_value = []  # No recent timeline entries
        mock_result2.scalars.return_value = mock_scalars2

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        service = ApplicationTrackingService(mock_db)
        stats = await service.get_application_stats(uuid4())

        assert stats.total_applications == 8
        # Active: applied(2) + screening(1) + interviewing(2) + offer_received(1) = 6
        assert stats.active_applications == 6
        # Interviews: interviewing(2) = 2
        assert stats.interviews_scheduled == 2
        # Offers: offer_received(1) = 1
        assert stats.offers_received == 1


class TestReminderQueries:
    """Tests for reminder query methods."""

    @pytest.fixture
    def service_with_mock_db(self):
        """Create service with mock db."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        return ApplicationTrackingService(mock_db), mock_db

    @pytest.mark.asyncio
    async def test_get_user_reminders_excludes_completed_by_default(
        self, service_with_mock_db
    ):
        """Test that completed reminders are excluded by default."""
        service, mock_db = service_with_mock_db

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        await service.get_user_reminders(uuid4())

        # Verify execute was called (query was built)
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_upcoming_reminders_time_window(self, service_with_mock_db):
        """Test upcoming reminders query with time window."""
        service, mock_db = service_with_mock_db

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        await service.get_upcoming_reminders(uuid4(), hours_ahead=48)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_overdue_reminders(self, service_with_mock_db):
        """Test overdue reminders query."""
        service, mock_db = service_with_mock_db

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        await service.get_overdue_reminders(uuid4())

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_application_timeline(self, service_with_mock_db):
        """Test getting application timeline."""
        service, mock_db = service_with_mock_db

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        await service.get_application_timeline(uuid4(), uuid4())

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_match_with_timeline(self, service_with_mock_db):
        """Test getting job match with full timeline loaded."""
        service, mock_db = service_with_mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_match_with_timeline(uuid4(), uuid4())

        assert result is None
        mock_db.execute.assert_called_once()


class TestAutoFollowUpReminder:
    """Tests for automatic follow-up reminder creation."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.delete = AsyncMock()
        mock.flush = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return ApplicationTrackingService(mock_db)

    @pytest.fixture
    def mock_job_match_with_job(self):
        """Create mock job match with job relationship."""
        job = MagicMock()
        job.id = uuid4()
        job.title = "Software Engineer at TechCorp"

        match = MagicMock(spec=JobMatch)
        match.id = uuid4()
        match.user_id = uuid4()
        match.job_id = job.id
        match.status = "saved"
        match.applied_at = None
        match.job = job
        return match

    @pytest.mark.asyncio
    async def test_create_auto_follow_up_creates_reminder(
        self, service, mock_db, mock_job_match_with_job
    ):
        """Test that auto follow-up creates a reminder when transitioning to APPLIED."""
        user_id = mock_job_match_with_job.user_id
        job_match_id = mock_job_match_with_job.id

        # First execute returns the job match, second returns no existing reminder
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_job_match_with_job

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None  # No existing follow-up

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        result = await service._create_auto_follow_up(
            user_id=user_id,
            job_match_id=job_match_id,
            job_match=mock_job_match_with_job,
        )

        # Verify reminder was added
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

        # Verify it's a follow-up type reminder
        added_reminder = mock_db.add.call_args[0][0]
        assert added_reminder.reminder_type == ReminderType.FOLLOW_UP.value
        assert added_reminder.user_id == user_id
        assert added_reminder.job_match_id == job_match_id
        assert "Follow up" in added_reminder.title

    @pytest.mark.asyncio
    async def test_create_auto_follow_up_skips_if_exists(
        self, service, mock_db, mock_job_match_with_job
    ):
        """Test that auto follow-up is not created if one already exists."""
        user_id = mock_job_match_with_job.user_id
        job_match_id = mock_job_match_with_job.id

        # Return an existing reminder
        existing_reminder = MagicMock(spec=ApplicationReminder)
        existing_reminder.id = uuid4()
        existing_reminder.reminder_type = ReminderType.FOLLOW_UP.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_reminder
        mock_db.execute.return_value = mock_result

        result = await service._create_auto_follow_up(
            user_id=user_id,
            job_match_id=job_match_id,
            job_match=mock_job_match_with_job,
        )

        # Should return None and not add anything
        assert result is None
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_auto_follow_up_uses_job_title(
        self, service, mock_db, mock_job_match_with_job
    ):
        """Test that auto follow-up uses the job title in the reminder."""
        user_id = mock_job_match_with_job.user_id
        job_match_id = mock_job_match_with_job.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service._create_auto_follow_up(
            user_id=user_id,
            job_match_id=job_match_id,
            job_match=mock_job_match_with_job,
        )

        # Verify the title includes the job title
        added_reminder = mock_db.add.call_args[0][0]
        assert "Software Engineer" in added_reminder.title

    @pytest.mark.asyncio
    async def test_create_auto_follow_up_scheduled_7_days_ahead(
        self, service, mock_db, mock_job_match_with_job
    ):
        """Test that auto follow-up is scheduled 7 days in the future."""
        user_id = mock_job_match_with_job.user_id
        job_match_id = mock_job_match_with_job.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        before = datetime.utcnow()
        result = await service._create_auto_follow_up(
            user_id=user_id,
            job_match_id=job_match_id,
            job_match=mock_job_match_with_job,
        )
        after = datetime.utcnow()

        # Verify scheduled_for is approximately 7 days from now
        added_reminder = mock_db.add.call_args[0][0]
        expected_min = before + timedelta(days=7)
        expected_max = after + timedelta(days=7)
        assert expected_min <= added_reminder.scheduled_for <= expected_max

    @pytest.mark.asyncio
    async def test_update_status_to_applied_creates_auto_follow_up(
        self, service, mock_db, mock_job_match_with_job
    ):
        """Test that transitioning to APPLIED status triggers auto follow-up creation."""
        mock_job_match_with_job.status = "saved"
        user_id = mock_job_match_with_job.user_id
        job_match_id = mock_job_match_with_job.id

        # First call returns job match, second call checks for existing reminder
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_job_match_with_job

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None  # No existing reminder

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        result = await service.update_application_status(
            user_id=user_id,
            job_match_id=job_match_id,
            new_status=ApplicationStatus.APPLIED,
        )

        # Verify status was updated
        assert mock_job_match_with_job.status == ApplicationStatus.APPLIED.value

        # Verify add was called twice (timeline entry + auto follow-up)
        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_update_status_to_non_applied_no_auto_follow_up(
        self, service, mock_db, mock_job_match_with_job
    ):
        """Test that non-APPLIED status transitions don't create auto follow-up."""
        mock_job_match_with_job.status = "new"
        user_id = mock_job_match_with_job.user_id
        job_match_id = mock_job_match_with_job.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_match_with_job
        mock_db.execute.return_value = mock_result

        result = await service.update_application_status(
            user_id=user_id,
            job_match_id=job_match_id,
            new_status=ApplicationStatus.VIEWED,
        )

        # Only timeline entry should be added, no auto follow-up
        assert mock_db.add.call_count == 1
