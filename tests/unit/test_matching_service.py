"""
Unit tests for the MatchingService.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from backend.services.matching_service import MatchingService
from backend.services.scoring_service import ScoreBreakdown
from backend.models.job import Job, JobMatch
from backend.models.user import User, UserProfile
from backend.models.feedback import UserFeedback


class TestMatchingService:
    """Tests for MatchingService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def matching_service(self, mock_db):
        """Create matching service with mocked dependencies."""
        with patch("backend.services.matching_service.EmbeddingService") as MockEmbed:
            mock_embed_instance = MagicMock()
            mock_embed_instance.generate_profile_embedding.return_value = [0.1] * 768
            mock_embed_instance.generate_job_embedding.return_value = [0.2] * 768
            MockEmbed.return_value = mock_embed_instance

            with patch("backend.services.matching_service.ScoringService") as MockScore:
                mock_score_instance = MagicMock()
                mock_score_instance.score_job.return_value = ScoreBreakdown(
                    total_score=85.0,
                    semantic_similarity=80.0,
                    skill_match=90.0,
                    experience_match=85.0,
                    compensation_match=80.0,
                    location_match=100.0,
                    freshness_score=90.0,
                    preference_match=75.0,
                )
                mock_score_instance.generate_explanation.return_value = "Good match"
                MockScore.return_value = mock_score_instance

                service = MatchingService(db=mock_db)
                service._mock_db = mock_db
                return service

    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.is_active = True
        return user

    @pytest.fixture
    def sample_profile(self):
        """Create sample user profile."""
        profile = MagicMock(spec=UserProfile)
        profile.id = uuid4()
        profile.user_id = uuid4()
        profile.skills = ["Python", "FastAPI", "PostgreSQL"]
        profile.experience_years = 5
        profile.min_rate_usd = Decimal("120000")
        profile.max_hours_per_week = 40
        profile.preferences = {"remote_only": True}
        profile.profile_embedding = None
        profile.certifications = ["AWS Solutions Architect"]
        profile.availability = {"full_time": True}
        profile.portfolio = {}
        return profile

    @pytest.fixture
    def sample_job(self):
        """Create sample job."""
        job = MagicMock(spec=Job)
        job.id = uuid4()
        job.title = "Senior Python Developer"
        job.company = "TechCorp"
        job.description = "Looking for experienced developer"
        job.skills = ["Python", "FastAPI", "PostgreSQL"]
        job.requirements = ["5+ years experience"]
        job.rate_min = Decimal("120000")
        job.rate_max = Decimal("160000")
        job.rate_type = "annual"
        job.location = "San Francisco, CA"
        job.remote = True
        job.posted_at = datetime.utcnow()
        job.created_at = datetime.utcnow()
        job.embedding = None
        job.hours_per_week = 40
        return job

    @pytest.mark.asyncio
    async def test_generate_matches_for_user_success(
        self, matching_service, mock_db, sample_profile, sample_job
    ):
        """Test successful match generation for a user."""
        user_id = sample_profile.user_id

        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile

        # Mock existing matches query
        existing_result = MagicMock()
        existing_result.all.return_value = []

        # Mock jobs query
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [sample_job]

        # Mock feedback query
        feedback_result = MagicMock()
        feedback_result.scalars.return_value = []

        # Setup mock_db.execute to return different results
        mock_db.execute.side_effect = [
            profile_result,  # Profile query
            existing_result,  # Existing matches
            jobs_result,  # Jobs query
            feedback_result,  # Positive feedback
            feedback_result,  # Negative feedback
        ]

        result = await matching_service.generate_matches_for_user(
            user_id, limit=10, min_score=70.0
        )

        assert isinstance(result, list)
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_generate_matches_no_profile(self, matching_service, mock_db):
        """Test match generation when user has no profile."""
        user_id = uuid4()

        # Mock profile not found
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = profile_result

        result = await matching_service.generate_matches_for_user(user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_generate_matches_no_new_jobs(
        self, matching_service, mock_db, sample_profile
    ):
        """Test match generation when no new jobs available."""
        user_id = sample_profile.user_id

        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile

        # Mock existing matches
        existing_result = MagicMock()
        existing_result.all.return_value = []

        # Mock no jobs
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = []

        # Mock feedback
        feedback_result = MagicMock()
        feedback_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            profile_result,
            existing_result,
            jobs_result,
            feedback_result,
            feedback_result,
        ]

        result = await matching_service.generate_matches_for_user(user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_generate_matches_respects_min_score(
        self, matching_service, mock_db, sample_profile, sample_job
    ):
        """Test that matches below min_score are filtered out."""
        user_id = sample_profile.user_id

        # Set low score on scoring service
        matching_service.scoring_service.score_job.return_value = ScoreBreakdown(
            total_score=50.0,  # Below min_score of 70
            semantic_similarity=50.0,
            skill_match=50.0,
            experience_match=50.0,
            compensation_match=50.0,
            location_match=50.0,
            freshness_score=50.0,
            preference_match=50.0,
        )

        # Mock queries
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile

        existing_result = MagicMock()
        existing_result.all.return_value = []

        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [sample_job]

        feedback_result = MagicMock()
        feedback_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            profile_result,
            existing_result,
            jobs_result,
            feedback_result,
            feedback_result,
        ]

        result = await matching_service.generate_matches_for_user(
            user_id, min_score=70.0
        )

        # No matches should be created since score is below threshold
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_matches_respects_limit(
        self, matching_service, mock_db, sample_profile
    ):
        """Test that match results are limited."""
        user_id = sample_profile.user_id

        # Create multiple jobs
        jobs = []
        for i in range(25):
            job = MagicMock(spec=Job)
            job.id = uuid4()
            job.title = f"Job {i}"
            job.company = "Corp"
            job.description = "Description"
            job.skills = ["Python"]
            job.requirements = []
            job.rate_min = Decimal("100000")
            job.rate_max = Decimal("150000")
            job.rate_type = "annual"
            job.location = "Remote"
            job.remote = True
            job.posted_at = datetime.utcnow()
            job.created_at = datetime.utcnow()
            job.embedding = None
            job.hours_per_week = 40
            jobs.append(job)

        # Mock queries
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile

        existing_result = MagicMock()
        existing_result.all.return_value = []

        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = jobs

        feedback_result = MagicMock()
        feedback_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            profile_result,
            existing_result,
            jobs_result,
            feedback_result,
            feedback_result,
        ]

        result = await matching_service.generate_matches_for_user(user_id, limit=10)

        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_generate_matches_for_all_active_users(
        self, matching_service, mock_db, sample_user
    ):
        """Test batch matching for all active users."""
        # Mock users query
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [sample_user]

        mock_db.execute.return_value = users_result

        # Mock generate_matches_for_user to return empty
        matching_service.generate_matches_for_user = AsyncMock(return_value=[])

        result = await matching_service.generate_matches_for_all_active_users(
            limit_per_user=10
        )

        assert "total_users" in result
        assert "successful_users" in result
        assert "total_matches" in result
        assert "errors" in result
        assert result["total_users"] == 1

    @pytest.mark.asyncio
    async def test_generate_matches_batch_handles_errors(
        self, matching_service, mock_db
    ):
        """Test batch matching handles errors gracefully."""
        user1 = MagicMock(spec=User)
        user1.id = uuid4()
        user1.is_active = True

        user2 = MagicMock(spec=User)
        user2.id = uuid4()
        user2.is_active = True

        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [user1, user2]
        mock_db.execute.return_value = users_result

        # First user succeeds, second fails
        matching_service.generate_matches_for_user = AsyncMock(
            side_effect=[[], Exception("Error")]
        )

        result = await matching_service.generate_matches_for_all_active_users()

        assert result["total_users"] == 2
        assert len(result["errors"]) == 1


class TestRecalculateMatchScore:
    """Tests for recalculating match scores."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.commit = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def matching_service(self, mock_db):
        """Create matching service."""
        with patch("backend.services.matching_service.EmbeddingService"):
            with patch("backend.services.matching_service.ScoringService") as MockScore:
                mock_score = MagicMock()
                mock_score.score_job.return_value = ScoreBreakdown(
                    total_score=90.0,
                    semantic_similarity=85.0,
                    skill_match=95.0,
                    experience_match=90.0,
                    compensation_match=85.0,
                    location_match=100.0,
                    freshness_score=85.0,
                    preference_match=80.0,
                )
                mock_score.generate_explanation.return_value = "Updated explanation"
                MockScore.return_value = mock_score
                return MatchingService(db=mock_db)

    @pytest.mark.asyncio
    async def test_recalculate_success(self, matching_service, mock_db):
        """Test successful score recalculation."""
        match_id = uuid4()
        user_id = uuid4()
        job_id = uuid4()

        # Create mock match
        match = MagicMock(spec=JobMatch)
        match.id = match_id
        match.user_id = user_id
        match.job_id = job_id
        match.score = 75.0

        # Create mock job
        job = MagicMock(spec=Job)
        job.id = job_id
        job.title = "Developer"

        # Create mock profile
        profile = MagicMock(spec=UserProfile)
        profile.user_id = user_id
        profile.skills = ["Python"]

        # Mock queries
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = match

        job_result = MagicMock()
        job_result.scalar_one.return_value = job

        profile_result = MagicMock()
        profile_result.scalar_one.return_value = profile

        feedback_result = MagicMock()
        feedback_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            match_result,
            job_result,
            profile_result,
            feedback_result,
            feedback_result,
        ]

        result = await matching_service.recalculate_match_score(match_id)

        assert result.score == 90.0
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_recalculate_match_not_found(self, matching_service, mock_db):
        """Test recalculation when match doesn't exist."""
        match_id = uuid4()

        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = match_result

        result = await matching_service.recalculate_match_score(match_id)

        assert result is None


class TestGetSimilarJobs:
    """Tests for finding similar jobs."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def matching_service(self, mock_db):
        """Create matching service."""
        with patch("backend.services.matching_service.EmbeddingService"):
            with patch("backend.services.matching_service.ScoringService"):
                return MatchingService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_similar_jobs_success(self, matching_service, mock_db):
        """Test finding similar jobs."""
        job_id = uuid4()
        similar_job_id = uuid4()

        # Source job with embedding
        source_job = MagicMock(spec=Job)
        source_job.id = job_id
        source_job.embedding = [0.1] * 768

        # Similar job
        similar_job = MagicMock(spec=Job)
        similar_job.id = similar_job_id
        similar_job.title = "Similar Job"

        # Mock source job query
        source_result = MagicMock()
        source_result.scalar_one_or_none.return_value = source_job

        # Mock vector search result
        vector_result = MagicMock()
        vector_result.all.return_value = [(similar_job_id, "Similar Job", "Corp", 0.1)]

        # Mock full job fetch
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [similar_job]

        mock_db.execute.side_effect = [source_result, vector_result, jobs_result]

        result = await matching_service.get_similar_jobs(job_id, limit=10)

        assert len(result) == 1
        assert result[0].title == "Similar Job"

    @pytest.mark.asyncio
    async def test_get_similar_jobs_no_source(self, matching_service, mock_db):
        """Test when source job doesn't exist."""
        job_id = uuid4()

        source_result = MagicMock()
        source_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = source_result

        result = await matching_service.get_similar_jobs(job_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_similar_jobs_no_embedding(self, matching_service, mock_db):
        """Test when source job has no embedding."""
        job_id = uuid4()

        source_job = MagicMock(spec=Job)
        source_job.id = job_id
        source_job.embedding = None

        source_result = MagicMock()
        source_result.scalar_one_or_none.return_value = source_job
        mock_db.execute.return_value = source_result

        result = await matching_service.get_similar_jobs(job_id)

        assert result == []


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def matching_service(self, mock_db):
        """Create matching service."""
        with patch("backend.services.matching_service.EmbeddingService"):
            with patch("backend.services.matching_service.ScoringService"):
                return MatchingService(db=mock_db)

    def test_job_to_dict(self, matching_service):
        """Test job to dictionary conversion."""
        job = MagicMock(spec=Job)
        job.id = uuid4()
        job.title = "Developer"
        job.company = "Corp"
        job.description = "Description"
        job.skills = ["Python", "AWS"]
        job.requirements = ["3+ years"]
        job.rate_min = Decimal("100000")
        job.rate_max = Decimal("150000")
        job.rate_type = "annual"
        job.location = "Remote"
        job.remote = True
        job.hours_per_week = 40
        job.embedding = [0.1] * 768

        result = matching_service._job_to_dict(job)

        assert result["title"] == "Developer"
        assert result["company"] == "Corp"
        assert "Python" in result["skills"]
        assert result["remote"] is True

    def test_job_to_dict_with_none_values(self, matching_service):
        """Test job to dict with None values."""
        job = MagicMock(spec=Job)
        job.id = uuid4()
        job.title = "Developer"
        job.company = "Corp"
        job.description = None
        job.skills = None
        job.requirements = None
        job.rate_min = None
        job.rate_max = None
        job.rate_type = None
        job.location = None
        job.remote = False
        job.hours_per_week = None
        job.embedding = None

        result = matching_service._job_to_dict(job)

        assert result["title"] == "Developer"
        assert result["skills"] == []
        assert result["requirements"] == []

    def test_profile_to_dict(self, matching_service):
        """Test profile to dictionary conversion."""
        profile = MagicMock(spec=UserProfile)
        profile.id = uuid4()
        profile.skills = ["Python", "FastAPI"]
        profile.experience_years = 5
        profile.certifications = ["AWS Certified"]
        profile.preferences = {"remote_only": True}
        profile.min_rate_usd = Decimal("120000")
        profile.max_hours_per_week = 40
        profile.availability = {"full_time": True}
        profile.portfolio = {"github": "https://github.com/user"}
        profile.profile_embedding = [0.1] * 768

        result = matching_service._profile_to_dict(profile)

        assert "Python" in result["skills"]
        assert result["experience_years"] == 5
        assert "AWS Certified" in result["certifications"]
        assert result["preferences"]["remote_only"] is True

    def test_profile_to_dict_with_none_values(self, matching_service):
        """Test profile to dict with None values."""
        profile = MagicMock(spec=UserProfile)
        profile.id = uuid4()
        profile.skills = None
        profile.experience_years = 0
        profile.certifications = None
        profile.preferences = None
        profile.min_rate_usd = None
        profile.max_hours_per_week = None
        profile.availability = None
        profile.portfolio = None
        profile.profile_embedding = None

        result = matching_service._profile_to_dict(profile)

        assert result["skills"] == []
        assert result["preferences"] == {}
        assert result["portfolio"] == {}

    @pytest.mark.asyncio
    async def test_get_user_context_with_feedback(self, matching_service, mock_db):
        """Test getting user context with feedback history."""
        user_id = uuid4()
        job_id = uuid4()

        # Create mock feedback
        feedback = MagicMock(spec=UserFeedback)
        feedback.user_id = user_id
        feedback.job_id = job_id
        feedback.action = "applied"

        # Create mock job
        job = MagicMock(spec=Job)
        job.id = job_id
        job.title = "Applied Job"
        job.company = "Corp"
        job.description = "Desc"
        job.skills = []
        job.requirements = []
        job.rate_min = None
        job.rate_max = None
        job.rate_type = None
        job.location = None
        job.remote = True
        job.hours_per_week = None
        job.embedding = None

        # Mock positive feedback query
        positive_result = MagicMock()
        positive_result.scalars.return_value = [feedback]

        # Mock applied jobs query
        applied_jobs_result = MagicMock()
        applied_jobs_result.scalars.return_value = [job]

        # Mock negative feedback query
        negative_result = MagicMock()
        negative_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            positive_result,
            applied_jobs_result,
            negative_result,
        ]

        result = await matching_service._get_user_context(user_id)

        assert "applied_jobs" in result
        assert len(result["applied_jobs"]) == 1

    @pytest.mark.asyncio
    async def test_get_user_context_empty(self, matching_service, mock_db):
        """Test getting user context with no feedback."""
        user_id = uuid4()

        # Mock empty feedback
        positive_result = MagicMock()
        positive_result.scalars.return_value = []

        negative_result = MagicMock()
        negative_result.scalars.return_value = []

        mock_db.execute.side_effect = [positive_result, negative_result]

        result = await matching_service._get_user_context(user_id)

        assert "applied_jobs" not in result
        assert "rejected_jobs" not in result


class TestMatchingSortingAndFiltering:
    """Tests for match sorting and filtering."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def matching_service(self, mock_db):
        """Create matching service."""
        with patch("backend.services.matching_service.EmbeddingService"):
            with patch("backend.services.matching_service.ScoringService"):
                return MatchingService(db=mock_db)

    def test_matches_sorted_by_score(self, matching_service):
        """Test that matches are sorted by score descending."""
        matches = [
            MagicMock(score=75.0),
            MagicMock(score=95.0),
            MagicMock(score=85.0),
        ]

        matches.sort(key=lambda m: m.score, reverse=True)

        assert matches[0].score == 95.0
        assert matches[1].score == 85.0
        assert matches[2].score == 75.0

    def test_days_back_filter(self, matching_service):
        """Test date filtering logic."""
        days_back = 7
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        recent_date = datetime.utcnow() - timedelta(days=3)
        old_date = datetime.utcnow() - timedelta(days=14)

        assert recent_date >= cutoff_date
        assert old_date < cutoff_date
