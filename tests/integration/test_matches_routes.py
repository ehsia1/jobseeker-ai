"""
Integration tests for job match routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4


class TestCreateMatch:
    """Tests for POST /matches/."""

    @pytest.mark.asyncio
    async def test_create_match_success(
        self, test_client: AsyncClient, user_factory, job_factory, db_session, auth_headers
    ):
        """Test creating a job match successfully."""
        user = await user_factory()
        job = await job_factory(title="Python Developer")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/matches/",
            json={"job_id": str(job.id)},
            headers=headers
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["status"] == "new"

    @pytest.mark.asyncio
    async def test_create_match_invalid_job(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test creating match with invalid job fails."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_job_id = str(uuid4())
        response = await test_client.post(
            "/matches/",
            json={"job_id": fake_job_id},
            headers=headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_match_duplicate(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test creating duplicate match returns existing."""
        user = await user_factory()
        job = await job_factory()
        existing_match = await job_match_factory(user=user, job=job, score=85.0)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/matches/",
            json={"job_id": str(job.id)},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(existing_match.id)

    @pytest.mark.asyncio
    async def test_create_match_unauthorized(
        self, test_client: AsyncClient, job_factory, db_session
    ):
        """Test creating match without auth fails."""
        job = await job_factory()
        await db_session.commit()

        response = await test_client.post(
            "/matches/",
            json={"job_id": str(job.id)}
        )

        assert response.status_code == 401


class TestGetUserMatches:
    """Tests for GET /matches/."""

    @pytest.mark.asyncio
    async def test_get_matches_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting user's job matches."""
        user = await user_factory()
        job1 = await job_factory(title="Job 1")
        job2 = await job_factory(title="Job 2")
        match1 = await job_match_factory(user=user, job=job1, score=90)
        match2 = await job_match_factory(user=user, job=job2, score=75)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/matches/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_matches_with_status_filter(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test filtering matches by status."""
        user = await user_factory()
        job1 = await job_factory(title="Job 1")
        job2 = await job_factory(title="Job 2")
        match1 = await job_match_factory(user=user, job=job1, status="new")
        match2 = await job_match_factory(user=user, job=job2, status="saved")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/matches/",
            params={"status_filter": "saved"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        for match in data:
            assert match["status"] == "saved"

    @pytest.mark.asyncio
    async def test_get_matches_with_min_score(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test filtering matches by minimum score."""
        user = await user_factory()
        job1 = await job_factory(title="High Match")
        job2 = await job_factory(title="Low Match")
        match1 = await job_match_factory(user=user, job=job1, score=95)
        match2 = await job_match_factory(user=user, job=job2, score=60)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/matches/",
            params={"min_score": 80},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        for match in data:
            assert float(match["score"]) >= 80

    @pytest.mark.asyncio
    async def test_get_matches_pagination(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test pagination of matches."""
        user = await user_factory()

        for i in range(15):
            job = await job_factory(title=f"Job {i}")
            await job_match_factory(user=user, job=job, score=70 + i)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/matches/",
            params={"limit": 5, "offset": 0},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestGetMatch:
    """Tests for GET /matches/{match_id}/."""

    @pytest.mark.asyncio
    async def test_get_match_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting specific match."""
        user = await user_factory()
        job = await job_factory(title="Python Developer")
        match = await job_match_factory(user=user, job=job, score=88)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(f"/matches/{match.id}/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(match.id)
        assert float(data["score"]) == 88

    @pytest.mark.asyncio
    async def test_get_match_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting non-existent match."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_id = str(uuid4())
        response = await test_client.get(f"/matches/{fake_id}/", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_match_other_user(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting another user's match fails."""
        user1 = await user_factory(email="user1@example.com", username="user1test")
        user2 = await user_factory(email="user2@example.com", username="user2test")
        job = await job_factory()
        match = await job_match_factory(user=user1, job=job)
        await db_session.commit()

        # User2 tries to access user1's match
        headers = auth_headers(user2.username)
        response = await test_client.get(f"/matches/{match.id}/", headers=headers)

        assert response.status_code == 404


class TestUpdateMatchStatus:
    """Tests for PUT /matches/{match_id}/status/."""

    @pytest.mark.asyncio
    async def test_update_status_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test updating match status."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="new")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            f"/matches/{match.id}/status/",
            json={"status": "saved"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"

    @pytest.mark.asyncio
    async def test_update_status_to_applied(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test updating status to applied sets applied_at."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job, status="saved")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            f"/matches/{match.id}/status/",
            json={"status": "applied"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "applied"
        assert data.get("applied_at") is not None

    @pytest.mark.asyncio
    async def test_update_status_invalid(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test updating with invalid status fails."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            f"/matches/{match.id}/status/",
            json={"status": "invalid_status"},
            headers=headers
        )

        assert response.status_code == 400


class TestUpdateMatchNotes:
    """Tests for PUT /matches/{match_id}/notes/."""

    @pytest.mark.asyncio
    async def test_update_notes_success(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test updating match notes."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            f"/matches/{match.id}/notes/",
            json={"client_notes": "Great opportunity, follow up next week"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["client_notes"] == "Great opportunity, follow up next week"

    @pytest.mark.asyncio
    async def test_update_notes_clear(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test clearing match notes."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user=user, job=job)
        match.client_notes = "Old notes"
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            f"/matches/{match.id}/notes/",
            json={"client_notes": None},
            headers=headers
        )

        assert response.status_code == 200


class TestMatchStats:
    """Tests for GET /matches/stats/summary."""

    @pytest.mark.asyncio
    async def test_get_stats(
        self, test_client: AsyncClient, user_factory, job_factory, job_match_factory, db_session, auth_headers
    ):
        """Test getting match statistics."""
        user = await user_factory()

        # Create matches with various statuses
        for status in ["new", "saved", "applied", "new"]:
            job = await job_factory()
            await job_match_factory(user=user, job=job, status=status)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/matches/stats/summary", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_matches" in data or "message" in data
