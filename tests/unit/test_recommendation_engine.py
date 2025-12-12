"""Unit tests for RecommendationEngine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from backend.services.recommendation_engine import RecommendationEngine
from backend.models.recommendation import UserPreferenceModel


class TestRecommendationEngine:
    """Tests for RecommendationEngine."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def engine(self, mock_db):
        """Create engine instance with mock DB."""
        return RecommendationEngine(mock_db)

    @pytest.fixture
    def mock_preference_model(self):
        """Create a mock preference model."""
        model = MagicMock(spec=UserPreferenceModel)
        model.user_id = uuid4()
        model.confidence_score = 0.7
        model.total_interactions = 20
        model.positive_samples = 10
        model.negative_samples = 5
        model.skill_preferences = {"python": 0.8, "javascript": 0.5, "java": -0.3}
        model.company_preferences = {"techcorp": 0.9}
        model.learned_preferences = {"prefers_remote": 0.8, "prefers_high_pay": 0.6}
        model.weight_adjustments = {"skill_match": 1.2}
        model.model_version = "1.0.5"
        model.last_trained_at = datetime.utcnow()
        return model

    @pytest.fixture
    def mock_job(self):
        """Create a mock job."""
        job = MagicMock()
        job.id = uuid4()
        job.title = "Senior Python Developer"
        job.company = "TechCorp"
        job.skills = ["Python", "FastAPI", "PostgreSQL"]
        job.remote = True
        job.rate_min = 60.0
        job.rate_max = 90.0
        job.location = "Remote"
        job.rate_type = "hourly"
        return job

    @pytest.fixture
    def mock_profile(self):
        """Create a mock user profile."""
        profile = MagicMock()
        profile.id = uuid4()
        profile.user_id = uuid4()
        profile.skills = ["Python", "FastAPI", "Docker"]
        profile.experience_years = 5
        profile.min_rate_usd = 50.0
        profile.preferences = {"remote": True}
        return profile

    def test_constants(self, engine):
        """Test that engine constants are properly defined."""
        assert engine.MIN_INTERACTIONS_FOR_PERSONALIZATION == 5
        assert engine.LOW_CONFIDENCE < engine.MEDIUM_CONFIDENCE < engine.HIGH_CONFIDENCE
        assert engine.MIN_WEIGHT_MULTIPLIER < 1.0 < engine.MAX_WEIGHT_MULTIPLIER

    def test_calculate_confidence_no_data(self, engine):
        """Test confidence calculation with no data."""
        confidence = engine._calculate_confidence(
            positive_samples=0,
            negative_samples=0,
            total_interactions=0,
        )
        assert confidence == 0.0

    def test_calculate_confidence_low_data(self, engine):
        """Test confidence calculation with low data."""
        confidence = engine._calculate_confidence(
            positive_samples=2,
            negative_samples=1,
            total_interactions=5,
        )
        # Should be low confidence due to few samples
        assert 0.0 < confidence < 0.5

    def test_calculate_confidence_balanced_data(self, engine):
        """Test confidence calculation with balanced data."""
        confidence = engine._calculate_confidence(
            positive_samples=15,
            negative_samples=10,
            total_interactions=50,
        )
        # Should be higher confidence with balanced samples
        assert confidence > 0.5

    def test_calculate_confidence_high_data(self, engine):
        """Test confidence calculation with high data volume."""
        confidence = engine._calculate_confidence(
            positive_samples=30,
            negative_samples=20,
            total_interactions=100,
        )
        # Should be high confidence
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_calculate_ml_adjustment_insufficient_data(self, engine, mock_db):
        """Test ML adjustment with insufficient interactions."""
        user_id = uuid4()

        # Create low-data preference model
        low_data_model = MagicMock(spec=UserPreferenceModel)
        low_data_model.total_interactions = 3  # Below threshold
        low_data_model.confidence_score = 0.2
        low_data_model.skill_preferences = {}
        low_data_model.company_preferences = {}
        low_data_model.learned_preferences = {}

        mock_job = MagicMock()
        mock_job.skills = ["Python"]
        mock_job.company = "TestCo"
        mock_job.remote = True
        mock_job.rate_max = 100.0

        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, mock_job, low_data_model
        )

        assert adjustment == 0.0
        assert details.get("insufficient_data") == True

    @pytest.mark.asyncio
    async def test_calculate_ml_adjustment_skill_boost(
        self, engine, mock_preference_model, mock_job
    ):
        """Test ML adjustment applies skill boost."""
        user_id = uuid4()

        # Job has Python which user prefers
        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, mock_job, mock_preference_model
        )

        # Should have positive adjustment due to Python preference
        assert details["skill_boost"] > 0
        assert len(details["matched_skill_preferences"]) > 0

    @pytest.mark.asyncio
    async def test_calculate_ml_adjustment_company_boost(
        self, engine, mock_preference_model, mock_job
    ):
        """Test ML adjustment applies company boost."""
        user_id = uuid4()

        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, mock_job, mock_preference_model
        )

        # Company is TechCorp which user prefers (0.9)
        assert details["company_boost"] > 0

    @pytest.mark.asyncio
    async def test_calculate_ml_adjustment_remote_boost(
        self, engine, mock_preference_model, mock_job
    ):
        """Test ML adjustment applies remote preference boost."""
        user_id = uuid4()

        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, mock_job, mock_preference_model
        )

        # User prefers remote (0.8) and job is remote
        assert "remote_boost" in details
        assert details["remote_boost"] > 0

    @pytest.mark.asyncio
    async def test_calculate_ml_adjustment_clamped(
        self, engine, mock_db
    ):
        """Test that ML adjustment is clamped to bounds."""
        user_id = uuid4()

        # Create extreme preference model
        extreme_model = MagicMock(spec=UserPreferenceModel)
        extreme_model.total_interactions = 100
        extreme_model.confidence_score = 1.0
        extreme_model.skill_preferences = {
            "python": 1.0, "fastapi": 1.0, "postgresql": 1.0,
            "docker": 1.0, "kubernetes": 1.0
        }
        extreme_model.company_preferences = {"techcorp": 1.0}
        extreme_model.learned_preferences = {"prefers_remote": 1.0, "prefers_high_pay": 1.0}

        mock_job = MagicMock()
        mock_job.skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"]
        mock_job.company = "TechCorp"
        mock_job.remote = True
        mock_job.rate_max = 200.0

        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, mock_job, extreme_model
        )

        # Adjustment should be clamped to max_adjustment (15.0)
        assert adjustment <= 15.0
        assert adjustment >= -15.0

    @pytest.mark.asyncio
    async def test_get_or_create_preference_model_existing(
        self, engine, mock_db, mock_preference_model
    ):
        """Test getting existing preference model."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_preference_model
        mock_db.execute.return_value = mock_result

        model = await engine._get_or_create_preference_model(uuid4())

        assert model == mock_preference_model
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_preference_model_new(self, engine, mock_db):
        """Test creating new preference model."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        model = await engine._get_or_create_preference_model(uuid4())

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_recommendation(self, engine, mock_db):
        """Test logging a recommendation."""
        log = await engine._log_recommendation(
            user_id=uuid4(),
            job_id=uuid4(),
            base_score=75.0,
            ml_adjustment=5.0,
            final_score=80.0,
            algorithm_version="1.0.5",
            score_breakdown={"skill_boost": 3.0, "company_boost": 2.0},
        )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommendation_analytics_empty(self, engine, mock_db):
        """Test analytics with no recommendations."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        analytics = await engine.get_recommendation_analytics(uuid4())

        assert analytics["total_recommendations"] == 0
        assert analytics["view_rate"] == 0.0
        assert analytics["apply_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_recommendation_analytics_with_data(self, engine, mock_db):
        """Test analytics with recommendation data."""
        # Create mock recommendation logs
        logs = []
        for i in range(10):
            log = MagicMock()
            log.base_score = 70.0 + i
            log.ml_adjustment = 5.0
            log.final_score = 75.0 + i
            log.was_viewed = i < 8  # 80% viewed
            log.was_clicked = i < 5  # 50% clicked
            log.was_saved = i < 3   # 30% saved
            log.was_applied = i < 2  # 20% applied
            logs.append(log)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = logs
        mock_db.execute.return_value = mock_result

        analytics = await engine.get_recommendation_analytics(uuid4())

        assert analytics["total_recommendations"] == 10
        assert analytics["view_rate"] == 0.8
        assert analytics["click_rate"] == 0.5
        assert analytics["save_rate"] == 0.3
        assert analytics["apply_rate"] == 0.2

    def test_calculate_preference_similarity_identical(self, engine):
        """Test similarity calculation for identical preferences."""
        model_a = MagicMock(spec=UserPreferenceModel)
        model_a.skill_preferences = {"python": 0.8, "javascript": 0.5}
        model_a.learned_preferences = {"prefers_remote": 0.8}

        model_b = MagicMock(spec=UserPreferenceModel)
        model_b.skill_preferences = {"python": 0.8, "javascript": 0.5}
        model_b.learned_preferences = {"prefers_remote": 0.8}

        similarity = engine._calculate_preference_similarity(model_a, model_b)

        # Should be very high similarity
        assert similarity > 0.9

    def test_calculate_preference_similarity_different(self, engine):
        """Test similarity calculation for different preferences."""
        model_a = MagicMock(spec=UserPreferenceModel)
        model_a.skill_preferences = {"python": 0.8, "javascript": 0.5}
        model_a.learned_preferences = {"prefers_remote": 0.8}

        model_b = MagicMock(spec=UserPreferenceModel)
        model_b.skill_preferences = {"java": 0.9, "c++": 0.7}
        model_b.learned_preferences = {"prefers_remote": 0.2}

        similarity = engine._calculate_preference_similarity(model_a, model_b)

        # Should be low similarity (no common skills)
        assert similarity < 0.3

    def test_calculate_preference_similarity_partial(self, engine):
        """Test similarity calculation for partially overlapping preferences."""
        model_a = MagicMock(spec=UserPreferenceModel)
        model_a.skill_preferences = {"python": 0.8, "javascript": 0.5, "react": 0.6}
        model_a.learned_preferences = {"prefers_remote": 0.7}

        model_b = MagicMock(spec=UserPreferenceModel)
        model_b.skill_preferences = {"python": 0.9, "java": 0.7, "react": 0.5}
        model_b.learned_preferences = {"prefers_remote": 0.8}

        similarity = engine._calculate_preference_similarity(model_a, model_b)

        # Should be moderate-to-high similarity (good overlap on python, react, remote)
        assert 0.3 < similarity < 0.9

    def test_calculate_preference_similarity_empty(self, engine):
        """Test similarity calculation with empty preferences."""
        model_a = MagicMock(spec=UserPreferenceModel)
        model_a.skill_preferences = {}
        model_a.learned_preferences = {}

        model_b = MagicMock(spec=UserPreferenceModel)
        model_b.skill_preferences = {"python": 0.8}
        model_b.learned_preferences = {}

        similarity = engine._calculate_preference_similarity(model_a, model_b)

        assert similarity == 0.0


class TestMLAdjustmentIntegration:
    """Integration-style tests for ML adjustment logic."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def engine(self, mock_db):
        return RecommendationEngine(mock_db)

    @pytest.mark.asyncio
    async def test_negative_skill_preference(self, engine):
        """Test that negative skill preferences reduce score."""
        user_id = uuid4()

        model = MagicMock(spec=UserPreferenceModel)
        model.total_interactions = 50
        model.confidence_score = 0.8
        model.skill_preferences = {"java": -0.7, "enterprise": -0.5}
        model.company_preferences = {}
        model.learned_preferences = {}

        # Job with disliked skills
        job = MagicMock()
        job.skills = ["Java", "Enterprise", "Spring"]
        job.company = "OtherCorp"
        job.remote = False
        job.rate_max = None

        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, job, model
        )

        # Should have negative adjustment
        assert details["skill_boost"] < 0

    @pytest.mark.asyncio
    async def test_mixed_skill_preferences(self, engine):
        """Test adjustment with mix of liked and disliked skills."""
        user_id = uuid4()

        model = MagicMock(spec=UserPreferenceModel)
        model.total_interactions = 50
        model.confidence_score = 0.8
        model.skill_preferences = {"python": 0.9, "java": -0.7}
        model.company_preferences = {}
        model.learned_preferences = {}

        # Job with mix of liked/disliked skills
        job = MagicMock()
        job.skills = ["Python", "Java"]
        job.company = "TestCorp"
        job.remote = False
        job.rate_max = None

        adjustment, details = await engine._calculate_ml_adjustment(
            user_id, job, model
        )

        # Adjustment should be based on average
        # Python: 0.9, Java: -0.7, average: 0.1
        assert -5 < details["skill_boost"] < 5
