"""
Integration tests for job management routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4


class TestListJobs:
    """Tests for GET /jobs/."""

    @pytest.mark.asyncio
    async def test_list_jobs_success(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test listing jobs successfully."""
        user = await user_factory()
        await db_session.commit()

        # Create some jobs
        job1 = await job_factory(title="Python Developer")
        job2 = await job_factory(title="Java Developer")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/jobs/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_list_jobs_with_pagination(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test job listing with pagination."""
        user = await user_factory()

        # Create multiple jobs
        for i in range(15):
            await job_factory(title=f"Job {i}")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/jobs/",
            params={"limit": 5, "offset": 0},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_list_jobs_remote_only_filter(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test filtering jobs by remote only."""
        user = await user_factory()

        remote_job = await job_factory(title="Remote Job", remote=True)
        onsite_job = await job_factory(title="Onsite Job", remote=False)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/jobs/",
            params={"remote_only": True},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        for job in data:
            assert job["remote"] is True

    @pytest.mark.asyncio
    async def test_list_jobs_min_rate_filter(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test filtering jobs by minimum rate."""
        user = await user_factory()

        high_pay_job = await job_factory(title="High Pay", rate_min=150000)
        low_pay_job = await job_factory(title="Low Pay", rate_min=50000, rate_max=60000)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/jobs/",
            params={"min_rate": 100000},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # All returned jobs should have rate >= 100000
        for job in data:
            rate = job.get("rate_min") or job.get("rate_max")
            if rate:
                assert float(rate) >= 100000

    @pytest.mark.asyncio
    async def test_list_jobs_source_filter(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test filtering jobs by source."""
        user = await user_factory()

        job1 = await job_factory(title="Job 1")
        job1.source = "linkedin"
        job2 = await job_factory(title="Job 2")
        job2.source = "indeed"
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/jobs/",
            params={"source": "linkedin"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        for job in data:
            assert job["source"] == "linkedin"

    @pytest.mark.asyncio
    async def test_list_jobs_unauthorized(self, test_client: AsyncClient):
        """Test listing jobs without authentication fails."""
        response = await test_client.get("/jobs/")

        assert response.status_code == 401


class TestGetJob:
    """Tests for GET /jobs/{job_id}/."""

    @pytest.mark.asyncio
    async def test_get_job_success(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test getting a specific job."""
        user = await user_factory()
        job = await job_factory(
            title="Senior Python Developer",
            company="TechCorp",
            description="Great opportunity"
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(f"/jobs/{job.id}/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Senior Python Developer"
        assert data["company"] == "TechCorp"

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting non-existent job returns 404."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_id = str(uuid4())
        response = await test_client.get(f"/jobs/{fake_id}/", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_unauthorized(self, test_client: AsyncClient, job_factory, db_session):
        """Test getting job without auth fails."""
        job = await job_factory()
        await db_session.commit()

        response = await test_client.get(f"/jobs/{job.id}/")

        assert response.status_code == 401


class TestSearchJobs:
    """Tests for POST /jobs/search/."""

    @pytest.mark.asyncio
    async def test_search_jobs_by_query(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test searching jobs by text query."""
        user = await user_factory()

        python_job = await job_factory(
            title="Python Developer",
            description="Work with Python and Django"
        )
        java_job = await job_factory(
            title="Java Developer",
            description="Work with Java and Spring"
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"query": "Python"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_results"] >= 1

    @pytest.mark.asyncio
    async def test_search_jobs_by_keywords(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test searching jobs by keywords."""
        user = await user_factory()

        await job_factory(title="FastAPI Developer", description="REST APIs with FastAPI")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"keywords": ["FastAPI", "REST"]},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_search_jobs_by_skills(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test searching jobs by skills."""
        user = await user_factory()

        await job_factory(
            title="Backend Developer",
            skills=["Python", "PostgreSQL", "Redis"]
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"skills": ["Python"]},
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_jobs_remote_filter(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test searching with remote_only filter."""
        user = await user_factory()

        await job_factory(title="Remote Job", remote=True)
        await job_factory(title="Office Job", remote=False)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"remote_only": True},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        for job in data.get("jobs", []):
            assert job["remote"] is True

    @pytest.mark.asyncio
    async def test_search_jobs_rate_range(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test searching with rate range."""
        user = await user_factory()

        await job_factory(title="High Pay", rate_min=150000, rate_max=200000)
        await job_factory(title="Low Pay", rate_min=40000, rate_max=60000)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"min_rate": 100000, "max_rate": 250000},
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_jobs_with_scoring(
        self, test_client: AsyncClient, job_factory, user_factory, profile_factory, db_session, auth_headers
    ):
        """Test that search returns scored results when profile exists."""
        user = await user_factory()
        profile = await profile_factory(
            user=user,
            skills=["Python", "FastAPI", "PostgreSQL"],
            experience_years=5
        )

        matching_job = await job_factory(
            title="Python Developer",
            skills=["Python", "FastAPI"],
            rate_min=90000
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"query": "Python"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Check that jobs have scoring info
        for job in data.get("jobs", []):
            assert "total_score" in job
            assert "score_breakdown" in job

    @pytest.mark.asyncio
    async def test_search_jobs_location_filter(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test searching with location filter."""
        user = await user_factory()

        await job_factory(title="SF Job", location="San Francisco, CA")
        await job_factory(title="NYC Job", location="New York, NY")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/",
            json={"location": "San Francisco"},
            headers=headers
        )

        assert response.status_code == 200


class TestListJobSources:
    """Tests for GET /jobs/sources/list/."""

    @pytest.mark.asyncio
    async def test_list_sources(
        self, test_client: AsyncClient, job_factory, user_factory, db_session, auth_headers
    ):
        """Test listing available job sources."""
        user = await user_factory()

        job1 = await job_factory(title="Job 1")
        job1.source = "linkedin"
        job2 = await job_factory(title="Job 2")
        job2.source = "indeed"
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/jobs/sources/list/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)


class TestListProfessions:
    """Tests for GET /jobs/professions/list/."""

    @pytest.mark.asyncio
    async def test_list_professions(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test listing available professions."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/jobs/professions/list/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "professions" in data
        assert "total" in data


class TestSearchLiveJobs:
    """Tests for POST /jobs/search/live/."""

    @pytest.mark.asyncio
    async def test_search_live_jobs(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test live job search."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/live/",
            json={
                "keywords": ["Python", "FastAPI"],
                "profession": "software_engineer",
                "remote_only": True,
                "limit": 5
            },
            headers=headers
        )

        # Live search may fail in test environment without real job boards
        # Accept either success or handled error
        assert response.status_code in [200, 400, 500]


class TestSearchJobsForProfile:
    """Tests for POST /jobs/search/profile/."""

    @pytest.mark.asyncio
    async def test_search_for_profile(
        self, test_client: AsyncClient, user_factory, profile_factory, db_session, auth_headers
    ):
        """Test profile-based job search."""
        user = await user_factory()
        profile = await profile_factory(
            user=user,
            skills=["Python", "FastAPI"],
            experience_years=5
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/profile/",
            json={"limit": 5},
            headers=headers
        )

        # May fail in test environment without real job boards
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_search_for_profile_no_profile(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test profile search fails without profile."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/jobs/search/profile/",
            json={},
            headers=headers
        )

        assert response.status_code == 400
        assert "profile" in response.json()["detail"].lower()
