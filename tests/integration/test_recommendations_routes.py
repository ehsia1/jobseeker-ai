"""Integration tests for recommendation API routes."""

import pytest
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User, UserProfile
from backend.models.job import Job, JobMatch
from backend.models.recommendation import UserPreferenceModel, RecommendationLog
from backend.models.feedback import UserFeedback


class TestRecommendationHealthRoute:
    """Tests for recommendation health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, test_client: AsyncClient):
        """Test health check returns expected data."""
        response = await test_client.get("/recommendations/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["ml_enabled"] == True
        assert "viewed" in data["supported_actions"]
        assert "applied" in data["supported_actions"]
        assert data["min_interactions_for_personalization"] == 5


class TestGetRecommendationsRoute:
    """Tests for GET /recommendations endpoint."""

    @pytest.mark.asyncio
    async def test_get_recommendations_no_profile(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test recommendations require user profile."""
        # Create user
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations",
            headers=headers,
        )

        # Should fail without profile
        assert response.status_code == 400
        assert "profile" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_recommendations_with_profile(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        profile_factory,
        job_factory,
        db_session: AsyncSession,
    ):
        """Test getting recommendations with valid profile."""
        # Create user with profile
        user = await user_factory()
        profile = await profile_factory(
            user,
            skills=["Python", "FastAPI", "PostgreSQL"],
        )

        # Create some test jobs
        for i in range(3):
            await job_factory(
                title=f"Python Developer {i}",
                skills=["Python", "FastAPI"],
            )

        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations",
            headers=headers,
            params={"limit": 10, "min_score": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "total" in data
        assert "model_confidence" in data
        assert "personalization_enabled" in data

    @pytest.mark.asyncio
    async def test_get_recommendations_empty_jobs(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        profile_factory,
        db_session: AsyncSession,
    ):
        """Test recommendations with no available jobs."""
        # Create user with profile
        user = await user_factory()
        await profile_factory(user, skills=["Python"])
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []
        assert data["total"] == 0


class TestUserPreferencesRoute:
    """Tests for user preferences endpoints."""

    @pytest.mark.asyncio
    async def test_get_preferences_new_user(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test getting preferences for new user creates default model."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/preferences",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user.id)
        assert data["confidence_score"] == 0.0
        assert data["total_interactions"] == 0
        assert data["skill_preferences"] == {}
        assert data["model_version"] is not None

    @pytest.mark.asyncio
    async def test_get_preferences_existing_model(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test getting existing preference model."""
        user = await user_factory()

        # Create preference model with data
        model = UserPreferenceModel(
            id=uuid4(),
            user_id=user.id,
            confidence_score=0.75,
            total_interactions=50,
            positive_samples=30,
            negative_samples=10,
            skill_preferences={"python": 0.8, "java": -0.3},
            company_preferences={"techcorp": 0.9},
            learned_preferences={"prefers_remote": 0.7},
            model_version="1.0.5",
        )
        db_session.add(model)
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/preferences",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["confidence_score"] == 0.75
        assert data["total_interactions"] == 50
        assert data["skill_preferences"]["python"] == 0.8
        assert data["company_preferences"]["techcorp"] == 0.9

    @pytest.mark.asyncio
    async def test_update_preferences(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test force updating preferences."""
        user = await user_factory()

        # Create preference model
        model = UserPreferenceModel(
            id=uuid4(),
            user_id=user.id,
            confidence_score=0.5,
            total_interactions=20,
        )
        db_session.add(model)
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.post(
            "/recommendations/preferences/update",
            headers=headers,
            json={"force_update": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user.id)


class TestRecommendationAnalyticsRoute:
    """Tests for recommendation analytics endpoint."""

    @pytest.mark.asyncio
    async def test_get_analytics_no_data(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test analytics with no recommendation history."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/analytics",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_recommendations"] == 0
        assert data["view_rate"] == 0.0
        assert data["apply_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_analytics_with_data(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        job_factory,
        db_session: AsyncSession,
    ):
        """Test analytics with recommendation history."""
        user = await user_factory()
        job = await job_factory()

        # Create some recommendation logs
        for i in range(10):
            log = RecommendationLog(
                id=uuid4(),
                user_id=user.id,
                job_id=job.id,
                base_score=70.0 + i,
                ml_adjustment=5.0,
                final_score=75.0 + i,
                algorithm_version="1.0.0",
                score_breakdown={"skill_boost": 5.0},
                was_viewed=i < 8,  # 80% view rate
                was_clicked=i < 5,  # 50% click rate
                was_applied=i < 2,  # 20% apply rate
            )
            db_session.add(log)

        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/analytics",
            headers=headers,
            params={"days_back": 30},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_recommendations"] == 10
        assert data["view_rate"] == 0.8
        assert data["click_rate"] == 0.5
        assert data["apply_rate"] == 0.2


class TestCollaborativeRecommendationsRoute:
    """Tests for collaborative filtering endpoint."""

    @pytest.mark.asyncio
    async def test_get_collaborative_recommendations(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test getting collaborative recommendations."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/collaborative",
            headers=headers,
            params={"limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "similar_users_found" in data


class TestFeedbackRoute:
    """Tests for feedback recording endpoint."""

    @pytest.mark.asyncio
    async def test_record_feedback_valid(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        job_factory,
        job_match_factory,
        db_session: AsyncSession,
    ):
        """Test recording valid feedback."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user, job)
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.post(
            "/recommendations/feedback",
            headers=headers,
            json={
                "job_id": str(job.id),
                "match_id": str(match.id),
                "action": "viewed",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "viewed"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_record_feedback_with_text(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        job_factory,
        job_match_factory,
        db_session: AsyncSession,
    ):
        """Test recording feedback with text comment."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user, job)
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.post(
            "/recommendations/feedback",
            headers=headers,
            json={
                "job_id": str(job.id),
                "match_id": str(match.id),
                "action": "rejected",
                "feedback_text": "Rate too low for my experience",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "rejected"
        assert data["feedback_type"] == "negative"

    @pytest.mark.asyncio
    async def test_record_feedback_applied(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        job_factory,
        job_match_factory,
        db_session: AsyncSession,
    ):
        """Test recording applied feedback."""
        user = await user_factory()
        job = await job_factory()
        match = await job_match_factory(user, job)
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.post(
            "/recommendations/feedback",
            headers=headers,
            json={
                "job_id": str(job.id),
                "match_id": str(match.id),
                "action": "applied",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "applied"
        assert data["feedback_type"] == "positive"


class TestFeedbackStatsRoute:
    """Tests for feedback statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_feedback_stats_empty(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test feedback stats with no history."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/feedback/stats",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_interactions"] == 0

    @pytest.mark.asyncio
    async def test_get_feedback_stats_with_data(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test feedback stats with data."""
        user = await user_factory()

        # Create feedback entries
        job_id = uuid4()
        match_id = uuid4()

        for action, ftype in [
            ("viewed", "implicit"),
            ("clicked", "implicit"),
            ("saved", "positive"),
            ("applied", "positive"),
            ("rejected", "negative"),
        ]:
            feedback = UserFeedback(
                id=uuid4(),
                user_id=user.id,
                job_id=job_id,
                match_id=match_id,
                action=action,
                feedback_type=ftype,
            )
            db_session.add(feedback)

        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/feedback/stats",
            headers=headers,
            params={"days_back": 30},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_interactions"] == 5


class TestFeedbackHistoryRoute:
    """Tests for feedback history endpoint."""

    @pytest.mark.asyncio
    async def test_get_feedback_history(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test getting feedback history."""
        user = await user_factory()

        # Create some feedback
        job_id = uuid4()
        match_id = uuid4()

        for action in ["viewed", "clicked", "applied"]:
            feedback = UserFeedback(
                id=uuid4(),
                user_id=user.id,
                job_id=job_id,
                match_id=match_id,
                action=action,
                feedback_type="positive" if action == "applied" else "implicit",
            )
            db_session.add(feedback)

        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/feedback/history",
            headers=headers,
            params={"limit": 50, "days_back": 30},
        )

        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        assert data["total"] == 3


class TestTrainingDataRoute:
    """Tests for training data endpoint."""

    @pytest.mark.asyncio
    async def test_get_training_data(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test getting training data."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/training-data",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "positive_samples" in data
        assert "negative_samples" in data


class TestSkillAnalysisRoute:
    """Tests for skill analysis endpoint."""

    @pytest.mark.asyncio
    async def test_get_skill_analysis_empty(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test skill analysis with no feedback."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/skill-analysis",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skill_preferences"] == {}
        assert data["total_skills_analyzed"] == 0


class TestCompanyAnalysisRoute:
    """Tests for company analysis endpoint."""

    @pytest.mark.asyncio
    async def test_get_company_analysis_empty(
        self,
        test_client: AsyncClient,
        auth_headers,
        user_factory,
        db_session: AsyncSession,
    ):
        """Test company analysis with no feedback."""
        user = await user_factory()
        await db_session.commit()
        headers = auth_headers(user.username)

        response = await test_client.get(
            "/recommendations/company-analysis",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["company_preferences"] == {}
        assert data["total_companies_analyzed"] == 0


class TestAuthorizationRequired:
    """Tests verifying authorization is required."""

    @pytest.mark.asyncio
    async def test_recommendations_require_auth(self, test_client: AsyncClient):
        """Test recommendations endpoint requires auth."""
        response = await test_client.get("/recommendations")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_preferences_require_auth(self, test_client: AsyncClient):
        """Test preferences endpoint requires auth."""
        response = await test_client.get("/recommendations/preferences")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_analytics_require_auth(self, test_client: AsyncClient):
        """Test analytics endpoint requires auth."""
        response = await test_client.get("/recommendations/analytics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_feedback_require_auth(self, test_client: AsyncClient):
        """Test feedback endpoint requires auth."""
        response = await test_client.post(
            "/recommendations/feedback",
            json={"job_id": str(uuid4()), "match_id": str(uuid4()), "action": "viewed"},
        )
        assert response.status_code == 401
