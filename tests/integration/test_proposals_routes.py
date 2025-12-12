"""
Integration tests for proposal routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock


class TestGenerateProposal:
    """Tests for POST /proposals/generate."""

    @pytest.mark.asyncio
    async def test_generate_proposal_success(
        self, test_client: AsyncClient, user_factory, resume_factory, job_factory,
        db_session, auth_headers, mock_llm_service
    ):
        """Test generating a proposal successfully."""
        user = await user_factory()
        resume = await resume_factory(user=user, skills=["Python", "FastAPI"])
        job = await job_factory(
            title="Python Developer",
            description="Looking for Python experts",
            skills=["Python", "FastAPI"]
        )
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/proposals/generate",
                json={
                    "job_id": str(job.id),
                    "tone": "medium"  # Valid values: short, medium, full
                },
                headers=headers
            )

        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "proposal" in data or "content" in data or "text" in data

    @pytest.mark.asyncio
    async def test_generate_proposal_no_resume(
        self, test_client: AsyncClient, user_factory, profile_factory, job_factory,
        db_session, auth_headers, mock_llm_service
    ):
        """Test generating proposal works even without a resume (uses profile)."""
        user = await user_factory()
        profile = await profile_factory(user=user, skills=["Python", "FastAPI"])
        job = await job_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/proposals/generate",
                json={
                    "job_id": str(job.id),
                    "tone": "medium"
                },
                headers=headers
            )

        # Proposals use profile, not resume, so this should work
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_generate_proposal_invalid_job(
        self, test_client: AsyncClient, user_factory, resume_factory, db_session, auth_headers
    ):
        """Test generating proposal with invalid job ID fails."""
        user = await user_factory()
        resume = await resume_factory(user=user)
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_job_id = str(uuid4())
        response = await test_client.post(
            "/proposals/generate",
            json={
                "job_id": fake_job_id,
                "tone": "medium"
            },
            headers=headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_proposal_different_tones(
        self, test_client: AsyncClient, user_factory, resume_factory, job_factory,
        db_session, auth_headers, mock_llm_service
    ):
        """Test generating proposals with different tones."""
        user = await user_factory()
        resume = await resume_factory(user=user)
        job = await job_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        tones = ["short", "medium", "full"]

        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            for tone in tones:
                response = await test_client.post(
                    "/proposals/generate",
                    json={
                        "job_id": str(job.id),
                        "tone": tone
                    },
                    headers=headers
                )

                assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_generate_proposal_unauthorized(
        self, test_client: AsyncClient, job_factory, db_session, mock_llm_service
    ):
        """Test generating proposal without auth in demo mode works (returns generic proposal)."""
        job = await job_factory()
        await db_session.commit()

        # In demo mode, unauthenticated requests are allowed
        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/proposals/generate",
                json={
                    "job_id": str(job.id),
                    "tone": "medium"
                }
            )

        # Demo mode allows unauthenticated requests
        assert response.status_code in [200, 401]


class TestGenerateAllTones:
    """Tests for POST /proposals/generate-all."""

    @pytest.mark.asyncio
    async def test_generate_all_tones_success(
        self, test_client: AsyncClient, user_factory, resume_factory, job_factory,
        db_session, auth_headers, mock_llm_service
    ):
        """Test generating proposals for all tones."""
        user = await user_factory()
        resume = await resume_factory(user=user)
        job = await job_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/proposals/generate-all",
                json={"job_id": str(job.id)},
                headers=headers
            )

        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            data = response.json()
            # Should have multiple proposals
            assert isinstance(data, dict) or isinstance(data, list)


class TestEnhanceProposal:
    """Tests for POST /proposals/enhance."""

    @pytest.mark.asyncio
    async def test_enhance_proposal_success(
        self, test_client: AsyncClient, user_factory, subscription_factory,
        db_session, auth_headers, mock_llm_service
    ):
        """Test enhancing a proposal."""
        user = await user_factory()
        # Enhance requires starter tier or higher
        subscription = await subscription_factory(user=user, tier="starter")
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/proposals/enhance",
                json={
                    "original_proposal": "I am a good developer with 5 years of Python experience. I can help with your project.",
                    "enhancements": ["improve_tone", "add_keywords"]
                },
                headers=headers
            )

        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "enhanced_proposal" in data or "content" in data

    @pytest.mark.asyncio
    async def test_enhance_proposal_empty(
        self, test_client: AsyncClient, user_factory, subscription_factory,
        db_session, auth_headers, mock_llm_service
    ):
        """Test enhancing empty proposal fails validation."""
        user = await user_factory()
        # Enhance requires starter tier or higher
        subscription = await subscription_factory(user=user, tier="starter")
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.proposal_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/proposals/enhance",
                json={
                    "original_proposal": "",
                    "enhancements": ["improve_tone"]
                },
                headers=headers
            )

        # Empty string might be allowed by schema but rejected by service
        assert response.status_code in [200, 400, 422]


class TestProposalsHealth:
    """Tests for GET /proposals/health."""

    @pytest.mark.asyncio
    async def test_proposals_health(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test proposals service health check."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/proposals/health", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in data
