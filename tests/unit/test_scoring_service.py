"""
Unit tests for the ScoringService.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from backend.services.scoring_service import ScoringService, ScoreBreakdown
from backend.models.job import Job
from backend.models.user import UserProfile


class TestScoreBreakdown:
    """Tests for ScoreBreakdown dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        breakdown = ScoreBreakdown(
            total_score=85.0,
            semantic_similarity=80.0,
            skill_match=90.0,
            experience_match=85.0,
            compensation_match=75.0,
            location_match=100.0,
            freshness_score=90.0,
            preference_match=80.0,
        )

        result = breakdown.to_dict()

        assert result["total_score"] == 85.0
        assert result["skill_match"] == 90.0
        assert len(result) == 8


class TestScoringService:
    """Tests for ScoringService."""

    @pytest.fixture
    def scoring_service(self, mock_embedding_service):
        """Create scoring service with mocked dependencies."""
        return ScoringService(embedding_service=mock_embedding_service)

    @pytest.fixture
    def sample_job(self):
        """Create a sample job for testing."""
        job = MagicMock(spec=Job)
        job.title = "Senior Python Developer"
        job.company = "TechCorp"
        job.description = "Looking for an experienced Python developer"
        job.skills = ["Python", "FastAPI", "PostgreSQL", "AWS"]
        job.requirements = ["5+ years experience", "Python required"]
        job.rate_min = Decimal("120000")
        job.rate_max = Decimal("160000")
        job.rate_type = "annual"
        job.location = "San Francisco, CA"
        job.remote = True
        job.posted_at = datetime.utcnow() - timedelta(days=2)
        job.employment_type = "full-time"
        job.embedding = None
        return job

    @pytest.fixture
    def sample_profile(self):
        """Create a sample user profile for testing."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
        profile.experience_years = 6
        profile.min_rate_usd = Decimal("130000")
        profile.location = "San Francisco, CA"
        profile.preferences = {
            "remote_only": True,
            "industries": ["tech", "fintech"],
            "job_types": ["full-time"],
        }
        profile.profile_embedding = None
        return profile

    def test_score_job_returns_breakdown(self, scoring_service, sample_job, sample_profile):
        """Test that score_job returns a ScoreBreakdown."""
        result = scoring_service.score_job(sample_job, sample_profile)

        assert isinstance(result, ScoreBreakdown)
        assert 0 <= result.total_score <= 100
        assert 0 <= result.skill_match <= 100

    def test_skill_match_perfect_overlap(self, scoring_service, sample_job, sample_profile):
        """Test skill matching with perfect overlap."""
        sample_job.skills = ["Python", "FastAPI", "PostgreSQL"]
        sample_profile.skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]

        result = scoring_service._calculate_skill_match(sample_job, sample_profile)

        assert result >= 100.0  # 100% match + bonus for extra skills

    def test_skill_match_partial_overlap(self, scoring_service, sample_job, sample_profile):
        """Test skill matching with partial overlap."""
        sample_job.skills = ["Python", "Ruby", "Go", "Rust"]
        sample_profile.skills = ["Python", "FastAPI"]

        result = scoring_service._calculate_skill_match(sample_job, sample_profile)

        assert 20 <= result <= 40  # Only 1 of 4 skills match

    def test_skill_match_no_overlap(self, scoring_service, sample_job, sample_profile):
        """Test skill matching with no overlap."""
        sample_job.skills = ["Java", "Spring", "Kotlin"]
        sample_profile.skills = ["Python", "FastAPI"]

        result = scoring_service._calculate_skill_match(sample_job, sample_profile)

        assert result == 0.0

    def test_skill_match_no_job_skills(self, scoring_service, sample_job, sample_profile):
        """Test skill matching when job has no skills listed."""
        sample_job.skills = []

        result = scoring_service._calculate_skill_match(sample_job, sample_profile)

        assert result == 100.0  # No requirements = full match

    def test_experience_match_within_range(self, scoring_service, sample_job, sample_profile):
        """Test experience matching when profile is within range."""
        sample_job.requirements = ["3-7 years experience required"]
        sample_profile.experience_years = 5

        result = scoring_service._calculate_experience_match(sample_job, sample_profile)

        assert result == 100.0

    def test_experience_match_under_qualified(self, scoring_service, sample_job, sample_profile):
        """Test experience matching when under-qualified."""
        sample_job.requirements = ["5+ years experience required"]
        sample_profile.experience_years = 2

        result = scoring_service._calculate_experience_match(sample_job, sample_profile)

        assert result < 100.0
        assert result >= 0.0

    def test_experience_match_over_qualified(self, scoring_service, sample_job, sample_profile):
        """Test experience matching when over-qualified."""
        sample_job.requirements = ["2-4 years experience required"]
        sample_profile.experience_years = 10

        result = scoring_service._calculate_experience_match(sample_job, sample_profile)

        # Over-qualified has small penalty but still good match
        assert result >= 70.0

    def test_experience_match_senior_title(self, scoring_service, sample_job, sample_profile):
        """Test experience extraction from senior job title."""
        sample_job.title = "Senior Software Engineer"
        sample_job.requirements = []
        sample_profile.experience_years = 7

        result = scoring_service._calculate_experience_match(sample_job, sample_profile)

        assert result == 100.0

    def test_experience_match_junior_title(self, scoring_service, sample_job, sample_profile):
        """Test experience extraction from junior job title."""
        sample_job.title = "Junior Developer"
        sample_job.requirements = []
        sample_profile.experience_years = 1

        result = scoring_service._calculate_experience_match(sample_job, sample_profile)

        assert result == 100.0

    def test_compensation_match_within_range(self, scoring_service, sample_job, sample_profile):
        """Test compensation matching when profile min is within job range."""
        sample_job.rate_min = Decimal("100000")
        sample_job.rate_max = Decimal("150000")
        sample_job.rate_type = "annual"
        sample_profile.min_rate_usd = Decimal("120000")

        result = scoring_service._calculate_compensation_match(sample_job, sample_profile)

        assert result == 100.0

    def test_compensation_match_job_pays_more(self, scoring_service, sample_job, sample_profile):
        """Test compensation when job pays more than expected."""
        sample_job.rate_min = Decimal("150000")
        sample_job.rate_max = Decimal("200000")
        sample_job.rate_type = "annual"
        sample_profile.min_rate_usd = Decimal("120000")

        result = scoring_service._calculate_compensation_match(sample_job, sample_profile)

        assert result == 100.0

    def test_compensation_match_job_pays_less(self, scoring_service, sample_job, sample_profile):
        """Test compensation when job pays less than expected."""
        sample_job.rate_min = Decimal("80000")
        sample_job.rate_max = Decimal("100000")
        sample_job.rate_type = "annual"
        sample_profile.min_rate_usd = Decimal("150000")

        result = scoring_service._calculate_compensation_match(sample_job, sample_profile)

        assert result < 100.0

    def test_compensation_hourly_conversion(self, scoring_service, sample_job, sample_profile):
        """Test hourly rate conversion to annual."""
        result = scoring_service._to_annual_rate(50.0, "hourly")

        expected = 50 * 2080  # 40 hours * 52 weeks
        assert result == expected

    def test_location_match_remote_job(self, scoring_service, sample_job, sample_profile):
        """Test location matching for remote job."""
        sample_job.remote = True
        sample_profile.preferences = {"remote_only": True}

        result = scoring_service._calculate_location_match(sample_job, sample_profile)

        assert result == 100.0

    def test_location_match_remote_required_but_not_offered(self, scoring_service, sample_job, sample_profile):
        """Test location matching when remote required but not offered."""
        sample_job.remote = False
        sample_job.location = "New York, NY"
        sample_profile.preferences = {"remote_only": True}
        sample_profile.location = "San Francisco, CA"

        result = scoring_service._calculate_location_match(sample_job, sample_profile)

        assert result == 25.0  # Heavy penalty

    def test_location_match_same_city(self, scoring_service, sample_job, sample_profile):
        """Test location matching for same city."""
        sample_job.remote = False
        sample_job.location = "San Francisco, CA"
        sample_profile.preferences = {}
        sample_profile.location = "San Francisco, CA"

        result = scoring_service._calculate_location_match(sample_job, sample_profile)

        assert result == 100.0

    def test_freshness_score_today(self, scoring_service, sample_job, sample_profile):
        """Test freshness score for job posted today."""
        sample_job.posted_at = datetime.utcnow()

        result = scoring_service._calculate_freshness_score(sample_job)

        assert result == 100.0

    def test_freshness_score_week_old(self, scoring_service, sample_job, sample_profile):
        """Test freshness score for week-old job."""
        sample_job.posted_at = datetime.utcnow() - timedelta(days=7)

        result = scoring_service._calculate_freshness_score(sample_job)

        assert result == 75.0

    def test_freshness_score_month_old(self, scoring_service, sample_job, sample_profile):
        """Test freshness score for month-old job."""
        sample_job.posted_at = datetime.utcnow() - timedelta(days=30)

        result = scoring_service._calculate_freshness_score(sample_job)

        assert result == 40.0

    def test_freshness_score_no_date(self, scoring_service, sample_job, sample_profile):
        """Test freshness score when no posting date."""
        sample_job.posted_at = None

        result = scoring_service._calculate_freshness_score(sample_job)

        assert result == 50.0

    def test_preference_match_industry(self, scoring_service, sample_job, sample_profile):
        """Test preference matching for industry."""
        sample_job.title = "Software Engineer"
        sample_job.company = "FinTech Startup"
        sample_job.description = "Join our fintech team"
        sample_profile.preferences = {"industries": ["fintech", "tech"]}

        result = scoring_service._calculate_preference_match(sample_job, sample_profile)

        assert result >= 75.0

    def test_preference_match_avoid_keywords(self, scoring_service, sample_job, sample_profile):
        """Test preference matching with avoid keywords."""
        sample_job.title = "PHP Developer"
        sample_job.description = "Looking for a PHP expert"
        sample_profile.preferences = {"avoid_keywords": ["php", "wordpress"]}

        result = scoring_service._calculate_preference_match(sample_job, sample_profile)

        assert result < 100.0

    def test_update_weights(self, scoring_service):
        """Test weight updating."""
        new_weights = {
            "semantic_similarity": 0.30,
            "skill_match": 0.30,
            "experience_match": 0.10,
            "compensation_match": 0.10,
            "location_match": 0.10,
            "freshness_score": 0.05,
            "preference_match": 0.05,
        }

        scoring_service.update_weights(new_weights)

        assert scoring_service.weights["semantic_similarity"] == 0.30
        assert scoring_service.weights["skill_match"] == 0.30

    def test_update_weights_invalid_sum(self, scoring_service):
        """Test that invalid weight sum raises error."""
        invalid_weights = {
            "semantic_similarity": 0.50,
            "skill_match": 0.50,
            "experience_match": 0.50,  # Sum > 1.0
            "compensation_match": 0.15,
            "location_match": 0.10,
            "freshness_score": 0.05,
            "preference_match": 0.05,
        }

        with pytest.raises(ValueError):
            scoring_service.update_weights(invalid_weights)

    def test_generate_explanation_excellent_match(self, scoring_service, sample_job, sample_profile):
        """Test explanation generation for excellent match."""
        breakdown = ScoreBreakdown(
            total_score=85.0,
            semantic_similarity=85.0,
            skill_match=90.0,
            experience_match=85.0,
            compensation_match=80.0,
            location_match=100.0,
            freshness_score=90.0,
            preference_match=80.0,
        )

        result = scoring_service.generate_explanation(sample_job, sample_profile, breakdown)

        assert "Excellent match" in result
        assert "Skills" in result

    def test_generate_explanation_weak_match(self, scoring_service, sample_job, sample_profile):
        """Test explanation generation for weak match."""
        breakdown = ScoreBreakdown(
            total_score=30.0,
            semantic_similarity=30.0,
            skill_match=20.0,
            experience_match=40.0,
            compensation_match=30.0,
            location_match=25.0,
            freshness_score=50.0,
            preference_match=30.0,
        )

        result = scoring_service.generate_explanation(sample_job, sample_profile, breakdown)

        assert "Weak match" in result

    def test_default_weights_sum_to_one(self, scoring_service):
        """Verify default weights sum to 1.0."""
        total = sum(scoring_service.DEFAULT_WEIGHTS.values())

        assert abs(total - 1.0) < 0.001


class TestExperienceYearExtraction:
    """Tests for experience year extraction from job descriptions."""

    @pytest.fixture
    def scoring_service(self, mock_embedding_service):
        return ScoringService(embedding_service=mock_embedding_service)

    @pytest.fixture
    def job(self):
        job = MagicMock(spec=Job)
        job.title = "Software Engineer"
        return job

    def test_extract_range(self, scoring_service, job):
        """Test extracting experience range."""
        job.requirements = ["3-5 years of experience required"]

        result = scoring_service._extract_experience_years(job)

        assert result == (3, 5)

    def test_extract_minimum(self, scoring_service, job):
        """Test extracting minimum experience."""
        job.requirements = ["5+ years experience"]

        result = scoring_service._extract_experience_years(job)

        assert result == 5

    def test_extract_from_title_senior(self, scoring_service, job):
        """Test extracting from senior title."""
        job.title = "Senior Developer"
        job.requirements = []

        result = scoring_service._extract_experience_years(job)

        assert result == 5

    def test_extract_from_title_junior(self, scoring_service, job):
        """Test extracting from junior title."""
        job.title = "Junior Software Engineer"
        job.requirements = []

        result = scoring_service._extract_experience_years(job)

        assert result == 0

    def test_extract_none_found(self, scoring_service, job):
        """Test when no experience requirement found."""
        job.title = "Software Engineer"
        job.requirements = ["Bachelor's degree required"]

        result = scoring_service._extract_experience_years(job)

        assert result is None
