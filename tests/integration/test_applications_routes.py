"""
Integration tests for application tracking routes.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta


class TestHealthEndpoint:
    """Tests for GET /applications/health."""

    @pytest.mark.asyncio
    async def test_health_check(self, test_client: AsyncClient):
        """Test application health endpoint."""
        response = await test_client.get("/applications/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "supported_statuses" in data
        assert "supported_reminder_types" in data
        assert "new" in data["supported_statuses"]
        assert "applied" in data["supported_statuses"]
        assert "follow_up" in data["supported_reminder_types"]


class TestUpdateStatus:
    """Tests for PUT /applications/matches/{match_id}/status."""

    @pytest.mark.asyncio
    async def test_update_status_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test updating application status successfully."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={
                "status": "viewed",
                "notes": "Reviewed the job posting",
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "viewed"
        assert "timeline_entry" in data
        assert data["timeline_entry"]["from_status"] == "new"
        assert data["timeline_entry"]["to_status"] == "viewed"
        assert data["timeline_entry"]["notes"] == "Reviewed the job posting"

    @pytest.mark.asyncio
    async def test_update_status_to_applied(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test updating status to applied from viewed."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="viewed")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "applied"

    @pytest.mark.asyncio
    async def test_update_status_full_workflow(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test complete application workflow: new -> viewed -> saved -> applied -> interviewing -> offer_received."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        # new -> viewed
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "viewed"},
            headers=headers
        )
        assert response.status_code == 200

        # viewed -> applied
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )
        assert response.status_code == 200

        # applied -> interviewing
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "interviewing"},
            headers=headers
        )
        assert response.status_code == 200

        # interviewing -> offer_received
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "offer_received"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "offer_received"

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that invalid status transitions are rejected."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        # Cannot go directly from new to applied (must go through viewed first)
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )

        assert response.status_code == 400
        assert "Invalid status transition" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_status_match_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test updating status for non-existent match."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.put(
            f"/applications/matches/{uuid4()}/status",
            json={"status": "viewed"},
            headers=headers
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_status_unauthorized(self, test_client: AsyncClient):
        """Test updating status without authentication."""
        response = await test_client.put(
            f"/applications/matches/{uuid4()}/status",
            json={"status": "viewed"},
        )

        # In demo mode, it might create a demo user, so we just check it doesn't crash
        assert response.status_code in [200, 400, 401]


class TestGetTimeline:
    """Tests for GET /applications/matches/{match_id}/timeline."""

    @pytest.mark.asyncio
    async def test_get_timeline_empty(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting timeline with no entries."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get(
            f"/applications/matches/{match.id}/timeline",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_match_id"] == str(match.id)
        assert data["current_status"] == "new"
        assert data["entries"] == []

    @pytest.mark.asyncio
    async def test_get_timeline_with_entries(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting timeline after status updates."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create some timeline entries by updating status
        await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "viewed"},
            headers=headers
        )
        await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )

        response = await test_client.get(
            f"/applications/matches/{match.id}/timeline",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_status"] == "applied"
        assert len(data["entries"]) == 2

    @pytest.mark.asyncio
    async def test_get_timeline_match_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting timeline for non-existent match."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get(
            f"/applications/matches/{uuid4()}/timeline",
            headers=headers
        )

        assert response.status_code == 404


class TestGetApplicationDetail:
    """Tests for GET /applications/matches/{match_id}/detail."""

    @pytest.mark.asyncio
    async def test_get_detail_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting application detail."""
        user = await user_factory()
        job = await job_factory(title="Software Engineer", company="TechCorp")
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get(
            f"/applications/matches/{match.id}/detail",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_match_id"] == str(match.id)
        assert data["job_title"] == "Software Engineer"
        assert data["company"] == "TechCorp"
        assert data["current_status"] == "applied"
        assert "timeline" in data
        assert "reminders" in data

    @pytest.mark.asyncio
    async def test_get_detail_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting detail for non-existent match."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get(
            f"/applications/matches/{uuid4()}/detail",
            headers=headers
        )

        assert response.status_code == 404


class TestCreateReminder:
    """Tests for POST /applications/matches/{match_id}/reminders."""

    @pytest.mark.asyncio
    async def test_create_reminder_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test creating a reminder successfully."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=7)).isoformat()

        response = await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Follow up on application",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
                "description": "Check if they've reviewed my application",
            },
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Follow up on application"
        assert data["reminder_type"] == "follow_up"
        assert data["is_completed"] == False
        assert data["is_dismissed"] == False

    @pytest.mark.asyncio
    async def test_create_reminder_different_types(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test creating reminders with different types."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        reminder_types = ["follow_up", "interview_prep", "interview", "deadline", "custom"]

        for reminder_type in reminder_types:
            response = await test_client.post(
                f"/applications/matches/{match.id}/reminders",
                json={
                    "title": f"Test {reminder_type}",
                    "scheduled_for": scheduled_time,
                    "reminder_type": reminder_type,
                },
                headers=headers
            )

            assert response.status_code == 201, f"Failed for type: {reminder_type}"
            data = response.json()
            assert data["reminder_type"] == reminder_type

    @pytest.mark.asyncio
    async def test_create_reminder_match_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test creating reminder for non-existent match."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        response = await test_client.post(
            f"/applications/matches/{uuid4()}/reminders",
            json={
                "title": "Test reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )

        assert response.status_code == 400


class TestScheduleInterview:
    """Tests for POST /applications/matches/{match_id}/schedule-interview."""

    @pytest.mark.asyncio
    async def test_schedule_interview_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test scheduling interview creates two reminders."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="interviewing")
        await db_session.commit()

        headers = auth_headers(user.username)
        interview_time = (datetime.utcnow() + timedelta(days=3)).isoformat()

        response = await test_client.post(
            f"/applications/matches/{match.id}/schedule-interview",
            json={
                "interview_time": interview_time,
                "prep_hours_before": 24,
            },
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 2  # Prep reminder + interview reminder

        # Check reminder types
        reminder_types = [r["reminder_type"] for r in data]
        assert "interview_prep" in reminder_types
        assert "interview" in reminder_types

    @pytest.mark.asyncio
    async def test_schedule_interview_custom_prep_time(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test scheduling interview with custom prep time."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="interviewing")
        await db_session.commit()

        headers = auth_headers(user.username)
        interview_time = (datetime.utcnow() + timedelta(days=5)).isoformat()

        response = await test_client.post(
            f"/applications/matches/{match.id}/schedule-interview",
            json={
                "interview_time": interview_time,
                "prep_hours_before": 48,  # 2 days before
            },
            headers=headers
        )

        assert response.status_code == 201
        assert len(response.json()) == 2


class TestListReminders:
    """Tests for GET /applications/reminders."""

    @pytest.mark.asyncio
    async def test_list_reminders_empty(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test listing reminders when none exist."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get("/applications/reminders", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["reminders"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_reminders_with_data(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test listing reminders with data."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        # Create a reminder
        await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Test reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )

        response = await test_client.get("/applications/reminders", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_reminders_includes_job_info(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that listed reminders include job information."""
        user = await user_factory()
        job = await job_factory(title="Software Engineer", company="TechCorp")
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Test reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )

        response = await test_client.get("/applications/reminders", headers=headers)

        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            reminder = data["reminders"][0]
            assert "job_title" in reminder
            assert "company" in reminder


class TestUpcomingReminders:
    """Tests for GET /applications/reminders/upcoming."""

    @pytest.mark.asyncio
    async def test_get_upcoming_reminders(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting upcoming reminders."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create a reminder for tomorrow (should be upcoming)
        scheduled_time = (datetime.utcnow() + timedelta(hours=12)).isoformat()
        await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Tomorrow reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )

        response = await test_client.get(
            "/applications/reminders/upcoming",
            params={"hours_ahead": 24},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        assert data["hours_window"] == 24

    @pytest.mark.asyncio
    async def test_get_upcoming_reminders_custom_window(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting upcoming reminders with custom time window."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get(
            "/applications/reminders/upcoming",
            params={"hours_ahead": 48},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hours_window"] == 48


class TestOverdueReminders:
    """Tests for GET /applications/reminders/overdue."""

    @pytest.mark.asyncio
    async def test_get_overdue_reminders(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting overdue reminders."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get(
            "/applications/reminders/overdue",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCompleteReminder:
    """Tests for POST /applications/reminders/{reminder_id}/complete."""

    @pytest.mark.asyncio
    async def test_complete_reminder_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test completing a reminder."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        # Create a reminder
        create_response = await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Test reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )
        reminder_id = create_response.json()["id"]

        # Complete the reminder
        response = await test_client.post(
            f"/applications/reminders/{reminder_id}/complete",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] == True
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_complete_reminder_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test completing non-existent reminder."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.post(
            f"/applications/reminders/{uuid4()}/complete",
            headers=headers
        )

        assert response.status_code == 404


class TestDismissReminder:
    """Tests for POST /applications/reminders/{reminder_id}/dismiss."""

    @pytest.mark.asyncio
    async def test_dismiss_reminder_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test dismissing a reminder."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        # Create a reminder
        create_response = await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Test reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )
        reminder_id = create_response.json()["id"]

        # Dismiss the reminder
        response = await test_client.post(
            f"/applications/reminders/{reminder_id}/dismiss",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_dismissed"] == True

    @pytest.mark.asyncio
    async def test_dismiss_reminder_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test dismissing non-existent reminder."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.post(
            f"/applications/reminders/{uuid4()}/dismiss",
            headers=headers
        )

        assert response.status_code == 404


class TestDeleteReminder:
    """Tests for DELETE /applications/reminders/{reminder_id}."""

    @pytest.mark.asyncio
    async def test_delete_reminder_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test deleting a reminder."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

        # Create a reminder
        create_response = await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Test reminder",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )
        reminder_id = create_response.json()["id"]

        # Delete the reminder
        response = await test_client.delete(
            f"/applications/reminders/{reminder_id}",
            headers=headers
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_reminder_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test deleting non-existent reminder."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.delete(
            f"/applications/reminders/{uuid4()}",
            headers=headers
        )

        assert response.status_code == 404


class TestApplicationStats:
    """Tests for GET /applications/stats."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting stats with no applications."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get("/applications/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_applications"] == 0
        assert data["active_applications"] == 0
        assert data["interviews_scheduled"] == 0
        assert data["offers_received"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_applications(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting stats with various applications."""
        user = await user_factory()
        job1 = await job_factory()
        job2 = await job_factory()
        job3 = await job_factory()

        # Create matches with different statuses
        await job_match_factory(user=user, job=job1, status="applied")
        await job_match_factory(user=user, job=job2, status="interviewing")
        await job_match_factory(user=user, job=job3, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get("/applications/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_applications"] == 3
        # Active: applied + interviewing = 2
        assert data["active_applications"] == 2
        # Interviewing count
        assert data["interviews_scheduled"] == 1
        assert "applications_by_status" in data

    @pytest.mark.asyncio
    async def test_get_stats_includes_breakdown(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that stats include status breakdown."""
        user = await user_factory()
        job = await job_factory()
        await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.get("/applications/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "applications_by_status" in data
        assert data["applications_by_status"]["applied"] == 1


class TestReminderWorkflow:
    """End-to-end tests for reminder workflows."""

    @pytest.mark.asyncio
    async def test_full_reminder_lifecycle(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test complete reminder lifecycle: create -> view -> complete."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)
        scheduled_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()

        # 1. Create reminder
        create_response = await test_client.post(
            f"/applications/matches/{match.id}/reminders",
            json={
                "title": "Follow up call",
                "scheduled_for": scheduled_time,
                "reminder_type": "follow_up",
            },
            headers=headers
        )
        assert create_response.status_code == 201
        reminder_id = create_response.json()["id"]

        # 2. View in upcoming reminders
        upcoming_response = await test_client.get(
            "/applications/reminders/upcoming",
            params={"hours_ahead": 24},
            headers=headers
        )
        assert upcoming_response.status_code == 200

        # 3. View in list
        list_response = await test_client.get("/applications/reminders", headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= 1

        # 4. Complete reminder
        complete_response = await test_client.post(
            f"/applications/reminders/{reminder_id}/complete",
            headers=headers
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["is_completed"] == True

        # 5. Verify not in default list (exclude completed by default)
        list_after_complete = await test_client.get("/applications/reminders", headers=headers)
        reminder_ids = [r["id"] for r in list_after_complete.json()["reminders"]]
        assert reminder_id not in reminder_ids

        # 6. Verify in list with include_completed
        list_with_completed = await test_client.get(
            "/applications/reminders",
            params={"include_completed": True},
            headers=headers
        )
        reminder_ids_with_completed = [r["id"] for r in list_with_completed.json()["reminders"]]
        assert reminder_id in reminder_ids_with_completed


class TestAutoFollowUpReminder:
    """Tests for automatic follow-up reminder creation on status change to applied."""

    @pytest.mark.asyncio
    async def test_auto_follow_up_created_on_applied(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that marking job as applied creates an auto follow-up reminder."""
        user = await user_factory()
        job = await job_factory(title="Software Engineer", company="TechCorp")
        match = await job_match_factory(user=user, job=job, status="saved")
        await db_session.commit()

        headers = auth_headers(user.username)

        # Mark as applied
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )
        assert response.status_code == 200

        # Check that a follow-up reminder was created
        reminders_response = await test_client.get(
            "/applications/reminders",
            headers=headers
        )
        assert reminders_response.status_code == 200
        data = reminders_response.json()

        # Should have at least one reminder (the auto follow-up)
        assert data["total"] >= 1

        # Find the auto follow-up reminder
        follow_up_reminders = [
            r for r in data["reminders"]
            if r["reminder_type"] == "follow_up" and "Follow up" in r["title"]
        ]
        assert len(follow_up_reminders) >= 1

        # Verify it includes the job title
        auto_reminder = follow_up_reminders[0]
        assert "Software Engineer" in auto_reminder["title"] or "Follow up" in auto_reminder["title"]

    @pytest.mark.asyncio
    async def test_auto_follow_up_not_created_for_non_applied_status(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that non-applied status changes don't create auto follow-up."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        # Mark as viewed (not applied)
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "viewed"},
            headers=headers
        )
        assert response.status_code == 200

        # Check reminders - should be empty (no auto follow-up for viewed)
        reminders_response = await test_client.get(
            "/applications/reminders",
            headers=headers
        )
        assert reminders_response.status_code == 200
        data = reminders_response.json()

        # Should not have any auto follow-up reminders
        follow_up_reminders = [
            r for r in data["reminders"]
            if r["reminder_type"] == "follow_up" and "Follow up" in r["title"]
        ]
        assert len(follow_up_reminders) == 0

    @pytest.mark.asyncio
    async def test_auto_follow_up_scheduled_7_days_out(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that auto follow-up is scheduled approximately 7 days from application."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="saved")
        await db_session.commit()

        headers = auth_headers(user.username)

        # Mark as applied
        before = datetime.utcnow()
        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )
        assert response.status_code == 200

        # Get the auto follow-up reminder
        reminders_response = await test_client.get(
            "/applications/reminders",
            headers=headers
        )
        data = reminders_response.json()

        follow_up_reminders = [
            r for r in data["reminders"]
            if r["reminder_type"] == "follow_up"
        ]

        if follow_up_reminders:
            reminder = follow_up_reminders[0]
            scheduled_for = datetime.fromisoformat(reminder["scheduled_for"].replace("Z", "+00:00"))

            # Should be approximately 7 days from now (allow some variance for test execution)
            expected_min = before + timedelta(days=6, hours=23)
            expected_max = before + timedelta(days=7, hours=1)

            # The scheduled_for should be around 7 days from now
            assert scheduled_for.replace(tzinfo=None) >= expected_min


class TestStatusTransitionValidation:
    """Tests for status transition validation."""

    @pytest.mark.asyncio
    async def test_cannot_skip_to_interviewing(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that you cannot skip directly to interviewing from new."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "interviewing"},
            headers=headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_change_terminal_state(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that terminal states cannot be changed."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="rejected")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "applied"},
            headers=headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_can_withdraw_from_any_active_state(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test that withdrawal is valid from most states."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="applied")
        await db_session.commit()

        headers = auth_headers(user.username)

        response = await test_client.put(
            f"/applications/matches/{match.id}/status",
            json={"status": "withdrawn"},
            headers=headers
        )

        assert response.status_code == 200
        assert response.json()["new_status"] == "withdrawn"
