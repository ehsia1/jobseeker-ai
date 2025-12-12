"""
Unit tests for the EmbeddingService.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from backend.services.embedding_service import EmbeddingService
from backend.models.job import Job
from backend.models.user import UserProfile


class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    @patch("backend.services.embedding_service.SentenceTransformer")
    def test_init_loads_model(self, MockTransformer):
        """Test that initialization loads the sentence transformer model."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        MockTransformer.return_value = mock_model

        service = EmbeddingService()

        MockTransformer.assert_called_once_with("all-MiniLM-L6-v2")
        assert service.embedding_dim == 384

    @patch("backend.services.embedding_service.SentenceTransformer")
    def test_init_with_custom_model(self, MockTransformer):
        """Test initialization with custom model name."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        MockTransformer.return_value = mock_model

        service = EmbeddingService(model_name="all-mpnet-base-v2")

        MockTransformer.assert_called_once_with("all-mpnet-base-v2")
        assert service.embedding_dim == 768

    @patch("backend.services.embedding_service.SentenceTransformer")
    def test_init_sets_up_cache(self, MockTransformer):
        """Test that cache is initialized correctly."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        MockTransformer.return_value = mock_model

        service = EmbeddingService()

        assert service._embedding_cache == {}
        assert service._cache_size_limit == 1000


class TestGenerateTextEmbedding:
    """Tests for text embedding generation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.randn(384)
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    def test_generate_text_embedding_returns_array(self, mock_service):
        """Test that text embedding returns numpy array."""
        result = mock_service.generate_text_embedding("Hello world")

        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)

    def test_generate_text_embedding_uses_cache(self, mock_service):
        """Test that cache is used for repeated text."""
        text = "Test text for caching"

        # First call
        result1 = mock_service.generate_text_embedding(text)
        # Second call
        result2 = mock_service.generate_text_embedding(text)

        # Model should only be called once
        assert mock_service.model.encode.call_count == 1
        np.testing.assert_array_equal(result1, result2)

    def test_generate_text_embedding_different_text(self, mock_service):
        """Test that different text generates new embeddings."""
        mock_service.model.encode.side_effect = [
            np.array([1.0] * 384),
            np.array([2.0] * 384),
        ]

        result1 = mock_service.generate_text_embedding("Text one")
        result2 = mock_service.generate_text_embedding("Text two")

        assert mock_service.model.encode.call_count == 2
        assert not np.array_equal(result1, result2)

    def test_cache_size_limit_enforced(self, mock_service):
        """Test that cache doesn't exceed size limit."""
        mock_service._cache_size_limit = 3

        for i in range(5):
            mock_service.model.encode.return_value = np.array([float(i)] * 384)
            mock_service.generate_text_embedding(f"Text {i}")

        # Cache should not exceed limit
        assert len(mock_service._embedding_cache) <= 3


class TestGenerateJobEmbedding:
    """Tests for job embedding generation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.randn(384)
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    def test_generate_job_embedding_full_job(self, mock_service):
        """Test embedding generation with full job data."""
        job = {
            "title": "Senior Python Developer",
            "company": "TechCorp",
            "description": "Build scalable applications",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "requirements": {"experience_level": "senior"},
            "location": "San Francisco",
            "remote": True,
        }

        result = mock_service.generate_job_embedding(job)

        assert isinstance(result, np.ndarray)
        # Verify model was called with combined text
        call_args = mock_service.model.encode.call_args[0][0]
        assert "Title: Senior Python Developer" in call_args
        assert "Company: TechCorp" in call_args
        assert "Required Skills: Python, FastAPI, PostgreSQL" in call_args
        assert "Remote: Yes" in call_args

    def test_generate_job_embedding_minimal_job(self, mock_service):
        """Test embedding generation with minimal job data."""
        job = {"title": "Developer"}

        result = mock_service.generate_job_embedding(job)

        assert isinstance(result, np.ndarray)

    def test_generate_job_embedding_empty_job(self, mock_service):
        """Test embedding generation with empty job."""
        job = {}

        result = mock_service.generate_job_embedding(job)

        assert isinstance(result, np.ndarray)

    def test_generate_job_embedding_truncates_description(self, mock_service):
        """Test that long descriptions are truncated."""
        long_description = "A" * 5000
        job = {"title": "Developer", "description": long_description}

        mock_service.generate_job_embedding(job)

        call_args = mock_service.model.encode.call_args[0][0]
        # Description should be truncated to 2000 chars
        assert len(call_args) < 5000

    def test_generate_job_embedding_handles_skills_list(self, mock_service):
        """Test handling of skills as list."""
        job = {"title": "Developer", "skills": ["Python", "AWS", "Docker"]}

        mock_service.generate_job_embedding(job)

        call_args = mock_service.model.encode.call_args[0][0]
        assert "Python, AWS, Docker" in call_args

    def test_generate_job_embedding_handles_skills_string(self, mock_service):
        """Test handling of skills as string."""
        job = {"title": "Developer", "skills": "Python, AWS"}

        mock_service.generate_job_embedding(job)

        call_args = mock_service.model.encode.call_args[0][0]
        assert "Python, AWS" in call_args


class TestGenerateProfileEmbedding:
    """Tests for profile embedding generation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.randn(384)
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    def test_generate_profile_embedding_full_profile(self, mock_service):
        """Test embedding generation with full profile."""
        profile = MagicMock(spec=UserProfile)
        profile.profession = "software_engineer"
        profile.job_title = "Senior Developer"
        profile.skills = ["Python", "AWS", "Docker"]
        profile.experience = "8 years building scalable applications"
        profile.experience_years = 8
        profile.education = "BS Computer Science"
        profile.certifications = ["AWS Solutions Architect"]
        profile.preferences = {"remote_only": True, "industries": ["tech", "fintech"]}
        profile.location = "San Francisco"

        result = mock_service.generate_profile_embedding(profile)

        assert isinstance(result, np.ndarray)
        call_args = mock_service.model.encode.call_args[0][0]
        assert "Profession: software_engineer" in call_args
        assert "Current/Desired Role: Senior Developer" in call_args
        assert "Skills: Python, AWS, Docker" in call_args
        assert "Prefers remote work" in call_args

    def test_generate_profile_embedding_minimal_profile(self, mock_service):
        """Test embedding generation with minimal profile."""
        profile = MagicMock(spec=UserProfile)
        profile.profession = None
        profile.job_title = None
        profile.skills = None
        profile.experience = None
        profile.experience_years = None
        profile.education = None
        profile.certifications = None
        profile.preferences = None
        profile.location = None

        result = mock_service.generate_profile_embedding(profile)

        assert isinstance(result, np.ndarray)

    def test_generate_profile_embedding_uses_experience_years_fallback(self, mock_service):
        """Test that experience_years is used when experience is None."""
        profile = MagicMock(spec=UserProfile)
        profile.profession = "developer"
        profile.job_title = None
        profile.skills = None
        profile.experience = None
        profile.experience_years = 5
        profile.education = None
        profile.certifications = None
        profile.preferences = None
        profile.location = None

        mock_service.generate_profile_embedding(profile)

        call_args = mock_service.model.encode.call_args[0][0]
        assert "Years of Experience: 5" in call_args


class TestCalculateSimilarity:
    """Tests for similarity calculation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    def test_identical_embeddings_high_similarity(self, mock_service):
        """Test that identical embeddings have similarity 1.0."""
        embedding = np.array([1.0, 0.5, 0.3])

        result = mock_service.calculate_similarity(embedding, embedding)

        assert result == pytest.approx(1.0, rel=1e-5)

    def test_opposite_embeddings_low_similarity(self, mock_service):
        """Test that opposite embeddings have low similarity."""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([-1.0, 0.0, 0.0])

        result = mock_service.calculate_similarity(embedding1, embedding2)

        assert result == pytest.approx(0.0, rel=1e-5)

    def test_orthogonal_embeddings_medium_similarity(self, mock_service):
        """Test that orthogonal embeddings have similarity 0.5."""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])

        result = mock_service.calculate_similarity(embedding1, embedding2)

        assert result == pytest.approx(0.5, rel=1e-5)

    def test_similarity_range_0_to_1(self, mock_service):
        """Test that similarity is always in 0-1 range."""
        np.random.seed(42)
        for _ in range(10):
            embedding1 = np.random.randn(384)
            embedding2 = np.random.randn(384)

            result = mock_service.calculate_similarity(embedding1, embedding2)

            assert 0.0 <= result <= 1.0


class TestCalculateSkillOverlap:
    """Tests for skill overlap calculation."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    def test_perfect_overlap(self, mock_service):
        """Test perfect skill overlap."""
        job_skills = ["Python", "AWS", "Docker"]
        profile_skills = ["Python", "AWS", "Docker"]

        result = mock_service.calculate_skill_overlap(job_skills, profile_skills)

        assert result == 1.0

    def test_no_overlap(self, mock_service):
        """Test no skill overlap."""
        job_skills = ["Python", "AWS"]
        profile_skills = ["Java", "Azure"]

        result = mock_service.calculate_skill_overlap(job_skills, profile_skills)

        assert result == 0.0

    def test_partial_overlap(self, mock_service):
        """Test partial skill overlap."""
        job_skills = ["Python", "AWS", "Docker"]
        profile_skills = ["Python", "AWS", "Kubernetes"]

        result = mock_service.calculate_skill_overlap(job_skills, profile_skills)

        # 2 common / 4 total = 0.5
        assert result == pytest.approx(0.5, rel=1e-5)

    def test_case_insensitive(self, mock_service):
        """Test that skill matching is case insensitive."""
        job_skills = ["python", "AWS"]
        profile_skills = ["PYTHON", "aws"]

        result = mock_service.calculate_skill_overlap(job_skills, profile_skills)

        assert result == 1.0

    def test_empty_job_skills(self, mock_service):
        """Test with empty job skills."""
        job_skills = []
        profile_skills = ["Python", "AWS"]

        result = mock_service.calculate_skill_overlap(job_skills, profile_skills)

        assert result == 0.0

    def test_empty_profile_skills(self, mock_service):
        """Test with empty profile skills."""
        job_skills = ["Python", "AWS"]
        profile_skills = []

        result = mock_service.calculate_skill_overlap(job_skills, profile_skills)

        assert result == 0.0

    def test_none_skills(self, mock_service):
        """Test with None skills."""
        result = mock_service.calculate_skill_overlap(None, ["Python"])
        assert result == 0.0

        result = mock_service.calculate_skill_overlap(["Python"], None)
        assert result == 0.0


class TestUpdateJobEmbeddings:
    """Tests for batch job embedding updates."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.randn(384)
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        mock.commit = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_update_job_embeddings_success(self, mock_service, mock_db):
        """Test successful job embeddings update."""
        job1 = MagicMock(spec=Job)
        job1.id = uuid4()
        job1.title = "Python Developer"
        job1.company = "TechCorp"
        job1.description = "Build APIs"
        job1.skills = ["Python"]
        job1.requirements = {}
        job1.location = "SF"
        job1.remote = True

        job2 = MagicMock(spec=Job)
        job2.id = uuid4()
        job2.title = "Data Engineer"
        job2.company = "DataCo"
        job2.description = "Build pipelines"
        job2.skills = ["Python", "Spark"]
        job2.requirements = {}
        job2.location = "NYC"
        job2.remote = False

        result = await mock_service.update_job_embeddings(mock_db, [job1, job2])

        assert result == 2
        assert mock_db.execute.call_count == 2
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_embeddings_empty_list(self, mock_service, mock_db):
        """Test with empty job list."""
        result = await mock_service.update_job_embeddings(mock_db, [])

        assert result == 0
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_embeddings_handles_errors(self, mock_service, mock_db):
        """Test that errors in individual jobs don't stop processing."""
        job1 = MagicMock(spec=Job)
        job1.id = uuid4()
        job1.title = "Developer"
        job1.company = None
        job1.description = None
        job1.skills = None
        job1.requirements = None
        job1.location = None
        job1.remote = None

        # First call succeeds, second fails
        mock_db.execute = AsyncMock(side_effect=[None, Exception("DB error"), None])

        job2 = MagicMock(spec=Job)
        job2.id = uuid4()
        job2.title = "Engineer"
        job2.company = None
        job2.description = None
        job2.skills = None
        job2.requirements = None
        job2.location = None
        job2.remote = None

        job3 = MagicMock(spec=Job)
        job3.id = uuid4()
        job3.title = "Architect"
        job3.company = None
        job3.description = None
        job3.skills = None
        job3.requirements = None
        job3.location = None
        job3.remote = None

        result = await mock_service.update_job_embeddings(mock_db, [job1, job2, job3])

        # Should have processed 2 successfully (job2 failed)
        assert result == 2


class TestUpdateProfileEmbedding:
    """Tests for profile embedding updates."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.randn(384)
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        mock.commit = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_update_profile_embedding_success(self, mock_service, mock_db):
        """Test successful profile embedding update."""
        profile = MagicMock(spec=UserProfile)
        profile.id = uuid4()
        profile.profession = "developer"
        profile.job_title = "Senior Engineer"
        profile.skills = ["Python"]
        profile.experience = None
        profile.experience_years = 5
        profile.education = None
        profile.certifications = None
        profile.preferences = None
        profile.location = None

        result = await mock_service.update_profile_embedding(mock_db, profile)

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_embedding_db_error(self, mock_service, mock_db):
        """Test handling of database error."""
        profile = MagicMock(spec=UserProfile)
        profile.id = uuid4()
        profile.profession = None
        profile.job_title = None
        profile.skills = None
        profile.experience = None
        profile.experience_years = None
        profile.education = None
        profile.certifications = None
        profile.preferences = None
        profile.location = None

        mock_db.execute.side_effect = Exception("DB error")

        result = await mock_service.update_profile_embedding(mock_db, profile)

        assert result is False


class TestFindSimilarJobs:
    """Tests for finding similar jobs."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked model."""
        with patch("backend.services.embedding_service.SentenceTransformer") as MockTransformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            MockTransformer.return_value = mock_model

            service = EmbeddingService()
            return service

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_find_similar_jobs_returns_sorted(self, mock_service, mock_db):
        """Test that similar jobs are returned sorted by similarity."""
        reference_embedding = np.array([1.0, 0.0, 0.0])

        job1 = MagicMock(spec=Job)
        job1.id = uuid4()
        job1.embedding = [0.9, 0.1, 0.0]  # High similarity

        job2 = MagicMock(spec=Job)
        job2.id = uuid4()
        job2.embedding = [0.5, 0.5, 0.0]  # Medium similarity

        job3 = MagicMock(spec=Job)
        job3.id = uuid4()
        job3.embedding = [0.0, 1.0, 0.0]  # Low similarity

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [job1, job2, job3]
        mock_db.execute.return_value = mock_result

        result = await mock_service.find_similar_jobs(
            mock_db, reference_embedding, limit=10, min_similarity=0.0
        )

        assert len(result) == 3
        # Results should be sorted by similarity descending
        assert result[0][0] == job1
        assert result[0][1] > result[1][1]
        assert result[1][1] > result[2][1]

    @pytest.mark.asyncio
    async def test_find_similar_jobs_respects_limit(self, mock_service, mock_db):
        """Test that limit parameter is respected."""
        reference_embedding = np.array([1.0, 0.0, 0.0])

        jobs = []
        for i in range(5):
            job = MagicMock(spec=Job)
            job.id = uuid4()
            job.embedding = [1.0 - i * 0.1, i * 0.1, 0.0]
            jobs.append(job)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = jobs
        mock_db.execute.return_value = mock_result

        result = await mock_service.find_similar_jobs(
            mock_db, reference_embedding, limit=2, min_similarity=0.0
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_similar_jobs_respects_min_similarity(self, mock_service, mock_db):
        """Test that minimum similarity threshold is respected."""
        reference_embedding = np.array([1.0, 0.0, 0.0])

        job_high = MagicMock(spec=Job)
        job_high.id = uuid4()
        job_high.embedding = [1.0, 0.0, 0.0]  # Similarity = 1.0

        job_low = MagicMock(spec=Job)
        job_low.id = uuid4()
        job_low.embedding = [0.0, 1.0, 0.0]  # Similarity = 0.5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [job_high, job_low]
        mock_db.execute.return_value = mock_result

        result = await mock_service.find_similar_jobs(
            mock_db, reference_embedding, limit=10, min_similarity=0.8
        )

        # Only high similarity job should be returned
        assert len(result) == 1
        assert result[0][0] == job_high

    @pytest.mark.asyncio
    async def test_find_similar_jobs_handles_null_embeddings(self, mock_service, mock_db):
        """Test handling of jobs with null embeddings."""
        reference_embedding = np.array([1.0, 0.0, 0.0])

        job_with_embedding = MagicMock(spec=Job)
        job_with_embedding.id = uuid4()
        job_with_embedding.embedding = [1.0, 0.0, 0.0]

        job_without_embedding = MagicMock(spec=Job)
        job_without_embedding.id = uuid4()
        job_without_embedding.embedding = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            job_with_embedding,
            job_without_embedding,
        ]
        mock_db.execute.return_value = mock_result

        result = await mock_service.find_similar_jobs(
            mock_db, reference_embedding, limit=10, min_similarity=0.0
        )

        assert len(result) == 1
        assert result[0][0] == job_with_embedding

    @pytest.mark.asyncio
    async def test_find_similar_jobs_empty_result(self, mock_service, mock_db):
        """Test with no jobs in database."""
        reference_embedding = np.array([1.0, 0.0, 0.0])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await mock_service.find_similar_jobs(
            mock_db, reference_embedding, limit=10, min_similarity=0.0
        )

        assert result == []
