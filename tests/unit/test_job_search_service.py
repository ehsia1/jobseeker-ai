"""
Unit tests for the JobSearchService.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from backend.services.job_search_service import JobSearchService
from backend.models.user import User, UserProfile
from backend.models.job import Job
from backend.searchers.base import SearchQuery, SearchResult


class TestJobSearchServiceInit:
    """Tests for JobSearchService initialization."""

    def test_init_creates_matching_service(self):
        """Test that initialization creates MatchingService."""
        mock_db = MagicMock()

        with patch("backend.services.job_search_service.MatchingService") as MockMatching:
            service = JobSearchService(mock_db)

            MockMatching.assert_called_once_with(mock_db)
            assert service.db == mock_db
            assert service.searchers == []


class TestSearchForUser:
    """Tests for user-based job search."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def mock_profile(self):
        """Create mock user profile."""
        profile = MagicMock(spec=UserProfile)
        profile.user_id = uuid4()
        profile.profession = "software_engineer"
        profile.skills = ["Python", "FastAPI", "PostgreSQL"]
        profile.preferences = {"remote_only": True}
        profile.min_rate_usd = Decimal("100000")
        return profile

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        return user

    @pytest.fixture
    def mock_search_result(self):
        """Create mock search result."""
        return SearchResult(
            source="test_board",
            source_id="job123",
            title="Python Developer",
            company="TechCorp",
            description="Build APIs with Python and FastAPI.",
            url="https://example.com/job/123",
            location="Remote",
            remote=True,
            salary_min=100000,
            salary_max=150000,
            salary_type="annual",
            skills=["Python", "FastAPI"],
            posted_date=datetime.now(),
            job_type="full-time",
            experience_level="senior",
            raw_data={},
        )

    @pytest.mark.asyncio
    async def test_search_for_user_no_profile(self, mock_db, mock_user):
        """Test search when user has no profile."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("backend.services.job_search_service.MatchingService"):
            service = JobSearchService(mock_db)
            result = await service.search_for_user(mock_user)

        assert result["error"] == "User profile not found"
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_for_user_success(
        self, mock_db, mock_user, mock_profile, mock_search_result
    ):
        """Test successful job search for user."""
        # Setup mock DB to return profile
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_profile,  # First call for profile lookup
            None,  # Second call for job exists check
        ]

        mock_searcher = MagicMock()
        mock_searcher.source_name = "test_board"
        mock_searcher.__aenter__ = AsyncMock(return_value=mock_searcher)
        mock_searcher.__aexit__ = AsyncMock(return_value=None)
        mock_searcher.search = AsyncMock(return_value=[mock_search_result])

        with patch("backend.services.job_search_service.MatchingService") as MockMatching:
            mock_matching = MagicMock()
            mock_matching.generate_matches_for_user = AsyncMock(return_value=5)
            MockMatching.return_value = mock_matching

            with patch(
                "backend.services.job_search_service.SearcherRegistry"
            ) as MockRegistry:
                MockRegistry.get_searchers_for_profession.return_value = [mock_searcher]
                MockRegistry.suggest_profession.return_value = "software_engineer"

                service = JobSearchService(mock_db)
                result = await service.search_for_user(mock_user)

        assert result["total_results"] == 1
        assert "source_stats" in result
        assert result["source_stats"]["test_board"] == 1

    @pytest.mark.asyncio
    async def test_search_for_user_with_custom_keywords(
        self, mock_db, mock_user, mock_profile
    ):
        """Test search with custom keywords."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_profile

        mock_searcher = MagicMock()
        mock_searcher.source_name = "test_board"
        mock_searcher.__aenter__ = AsyncMock(return_value=mock_searcher)
        mock_searcher.__aexit__ = AsyncMock(return_value=None)
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("backend.services.job_search_service.MatchingService"):
            with patch(
                "backend.services.job_search_service.SearcherRegistry"
            ) as MockRegistry:
                MockRegistry.get_searchers_for_profession.return_value = [mock_searcher]

                service = JobSearchService(mock_db)
                result = await service.search_for_user(
                    mock_user, custom_keywords=["AWS", "Docker"]
                )

        assert "results" in result

    @pytest.mark.asyncio
    async def test_search_handles_searcher_errors(self, mock_db, mock_user, mock_profile):
        """Test that searcher errors are handled gracefully."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_profile

        mock_searcher = MagicMock()
        mock_searcher.source_name = "failing_board"
        mock_searcher.__aenter__ = AsyncMock(return_value=mock_searcher)
        mock_searcher.__aexit__ = AsyncMock(return_value=None)
        mock_searcher.search = AsyncMock(side_effect=Exception("API Error"))

        with patch("backend.services.job_search_service.MatchingService"):
            with patch(
                "backend.services.job_search_service.SearcherRegistry"
            ) as MockRegistry:
                MockRegistry.get_searchers_for_profession.return_value = [mock_searcher]

                service = JobSearchService(mock_db)
                result = await service.search_for_user(mock_user)

        # Should not crash, just return empty results for that source
        assert result["total_results"] == 0


class TestSearchByKeywords:
    """Tests for keyword-based job search."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_search_by_keywords_with_profession(self, mock_db):
        """Test keyword search with specified profession."""
        mock_searcher = MagicMock()
        mock_searcher.source_name = "tech_board"
        mock_searcher.__aenter__ = AsyncMock(return_value=mock_searcher)
        mock_searcher.__aexit__ = AsyncMock(return_value=None)
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("backend.services.job_search_service.MatchingService"):
            with patch(
                "backend.services.job_search_service.SearcherRegistry"
            ) as MockRegistry:
                MockRegistry.get_searchers_for_profession.return_value = [mock_searcher]

                service = JobSearchService(mock_db)
                result = await service.search_by_keywords(
                    keywords=["Python", "AWS"], profession="software_engineer"
                )

        MockRegistry.get_searchers_for_profession.assert_called_once_with(
            "software_engineer"
        )
        assert "results" in result

    @pytest.mark.asyncio
    async def test_search_by_keywords_infers_profession(self, mock_db):
        """Test that profession is inferred from keywords."""
        mock_searcher = MagicMock()
        mock_searcher.source_name = "general_board"
        mock_searcher.__aenter__ = AsyncMock(return_value=mock_searcher)
        mock_searcher.__aexit__ = AsyncMock(return_value=None)
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("backend.services.job_search_service.MatchingService"):
            with patch(
                "backend.services.job_search_service.SearcherRegistry"
            ) as MockRegistry:
                MockRegistry.suggest_profession.return_value = "data_engineer"
                MockRegistry.get_searchers_for_profession.return_value = [mock_searcher]

                service = JobSearchService(mock_db)
                result = await service.search_by_keywords(keywords=["Spark", "Hadoop"])

        MockRegistry.suggest_profession.assert_called_once_with(["Spark", "Hadoop"])

    @pytest.mark.asyncio
    async def test_search_by_keywords_remote_only(self, mock_db):
        """Test remote_only parameter is passed to query."""
        mock_searcher = MagicMock()
        mock_searcher.source_name = "board"
        mock_searcher.__aenter__ = AsyncMock(return_value=mock_searcher)
        mock_searcher.__aexit__ = AsyncMock(return_value=None)
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("backend.services.job_search_service.MatchingService"):
            with patch(
                "backend.services.job_search_service.SearcherRegistry"
            ) as MockRegistry:
                MockRegistry.suggest_profession.return_value = "general"
                MockRegistry.get_searchers_for_profession.return_value = [mock_searcher]

                service = JobSearchService(mock_db)
                await service.search_by_keywords(
                    keywords=["Developer"], remote_only=False
                )

        # Verify search was called with correct query
        call_args = mock_searcher.search.call_args[0][0]
        assert call_args.remote_only is False


class TestBuildSearchQuery:
    """Tests for search query building."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_db = MagicMock()
        with patch("backend.services.job_search_service.MatchingService"):
            return JobSearchService(mock_db)

    def test_build_query_from_profile(self, service):
        """Test building query from user profile."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = ["Python", "AWS", "Docker"]
        profile.preferences = {"remote_only": True, "job_types": ["full-time"]}
        profile.min_rate_usd = Decimal("120000")

        query = service._build_search_query(profile, None, 20)

        assert "Python" in query.keywords
        assert query.remote_only is True
        assert query.min_rate == 120000.0
        assert query.limit == 20

    def test_build_query_with_custom_keywords(self, service):
        """Test query building with custom keywords."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = ["Python"]
        profile.preferences = {}
        profile.min_rate_usd = None

        query = service._build_search_query(profile, ["Kubernetes", "Terraform"], 15)

        assert "Python" in query.keywords
        assert "Kubernetes" in query.keywords
        assert "Terraform" in query.keywords

    def test_build_query_limits_keywords(self, service):
        """Test that keywords are limited to 10."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = [f"Skill{i}" for i in range(15)]
        profile.preferences = {}
        profile.min_rate_usd = None

        query = service._build_search_query(profile, None, 20)

        assert len(query.keywords) <= 10

    def test_build_query_no_skills(self, service):
        """Test query building with no skills."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = None
        profile.preferences = None
        profile.min_rate_usd = None

        query = service._build_search_query(profile, ["Custom"], 20)

        assert "Custom" in query.keywords

    def test_build_query_deduplicates_keywords(self, service):
        """Test that duplicate keywords are removed."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = ["Python", "AWS"]
        profile.preferences = {}
        profile.min_rate_usd = None

        query = service._build_search_query(profile, ["Python", "Docker"], 20)

        # Python should appear only once
        assert query.keywords.count("Python") <= 1


class TestDeduplicateResults:
    """Tests for result deduplication."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_db = MagicMock()
        with patch("backend.services.job_search_service.MatchingService"):
            return JobSearchService(mock_db)

    def test_deduplicate_removes_duplicates(self, service):
        """Test that duplicate results are removed."""
        result1 = SearchResult(
            source="board1",
            source_id="1",
            title="Python Developer",
            company="TechCorp",
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
        )
        result2 = SearchResult(
            source="board2",
            source_id="2",
            title="Python Developer",
            company="TechCorp",  # Same title and company
            description="Different description",
            url="https://example.com/2",
            location="Remote",
            remote=True,
        )

        unique = service._deduplicate_results([result1, result2])

        assert len(unique) == 1
        assert unique[0].source == "board1"  # First one is kept

    def test_deduplicate_keeps_unique(self, service):
        """Test that unique results are kept."""
        result1 = SearchResult(
            source="board1",
            source_id="1",
            title="Python Developer",
            company="TechCorp",
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
        )
        result2 = SearchResult(
            source="board2",
            source_id="2",
            title="Data Engineer",  # Different title
            company="DataCo",
            description="Build pipelines",
            url="https://example.com/2",
            location="Remote",
            remote=True,
        )

        unique = service._deduplicate_results([result1, result2])

        assert len(unique) == 2

    def test_deduplicate_case_insensitive(self, service):
        """Test that deduplication is case insensitive."""
        result1 = SearchResult(
            source="board1",
            source_id="1",
            title="PYTHON DEVELOPER",
            company="TECHCORP",
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
        )
        result2 = SearchResult(
            source="board2",
            source_id="2",
            title="python developer",
            company="techcorp",
            description="Different description",
            url="https://example.com/2",
            location="Remote",
            remote=True,
        )

        unique = service._deduplicate_results([result1, result2])

        assert len(unique) == 1

    def test_deduplicate_handles_null_company(self, service):
        """Test deduplication handles None company."""
        result1 = SearchResult(
            source="board1",
            source_id="1",
            title="Freelance Developer",
            company=None,
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
        )
        result2 = SearchResult(
            source="board2",
            source_id="2",
            title="Freelance Developer",
            company=None,
            description="Different description",
            url="https://example.com/2",
            location="Remote",
            remote=True,
        )

        unique = service._deduplicate_results([result1, result2])

        assert len(unique) == 1


class TestStoreSearchResults:
    """Tests for storing search results in database."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mocked dependencies."""
        with patch("backend.services.job_search_service.MatchingService"):
            return JobSearchService(mock_db)

    @pytest.mark.asyncio
    async def test_store_new_jobs(self, service, mock_db):
        """Test storing new jobs."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = SearchResult(
            source="board",
            source_id="123",
            title="Developer",
            company="Corp",
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
            skills=["Python"],
            posted_date=datetime.now(),
        )

        count = await service._store_search_results([result])

        assert count == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_skips_existing_jobs(self, service, mock_db):
        """Test that existing jobs are skipped."""
        existing_job = MagicMock(spec=Job)
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_job

        result = SearchResult(
            source="board",
            source_id="123",
            title="Developer",
            company="Corp",
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
        )

        count = await service._store_search_results([result])

        assert count == 0
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_handles_errors(self, service, mock_db):
        """Test that store errors are handled gracefully."""
        mock_db.execute.side_effect = Exception("DB Error")

        result = SearchResult(
            source="board",
            source_id="123",
            title="Developer",
            company="Corp",
            description="Build stuff",
            url="https://example.com/1",
            location="Remote",
            remote=True,
        )

        count = await service._store_search_results([result])

        # Should not crash, just skip the job
        assert count == 0


class TestSerializeResult:
    """Tests for result serialization."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_db = MagicMock()
        with patch("backend.services.job_search_service.MatchingService"):
            return JobSearchService(mock_db)

    def test_serialize_full_result(self, service):
        """Test serializing a complete search result."""
        posted_date = datetime(2024, 1, 15, 10, 30)
        result = SearchResult(
            source="tech_board",
            source_id="job123",
            title="Senior Python Developer",
            company="TechCorp",
            description="A" * 1000,  # Long description
            url="https://example.com/job/123",
            location="San Francisco, CA",
            remote=True,
            salary_min=140000,
            salary_max=180000,
            salary_type="annual",
            skills=["Python", "AWS"],
            posted_date=posted_date,
            job_type="full-time",
            experience_level="senior",
            raw_data={},
        )

        serialized = service._serialize_result(result)

        assert serialized["source"] == "tech_board"
        assert serialized["title"] == "Senior Python Developer"
        assert serialized["company"] == "TechCorp"
        assert len(serialized["description"]) == 500  # Truncated
        assert serialized["remote"] is True
        assert serialized["salary_min"] == 140000
        assert serialized["posted_date"] == posted_date.isoformat()
        assert serialized["skills"] == ["Python", "AWS"]

    def test_serialize_minimal_result(self, service):
        """Test serializing a minimal search result."""
        result = SearchResult(
            source="board",
            source_id="1",
            title="Developer",
            company=None,
            description="Short desc",
            url="https://example.com",
            location=None,
            remote=False,
        )

        serialized = service._serialize_result(result)

        assert serialized["source"] == "board"
        assert serialized["company"] is None
        assert serialized["posted_date"] is None
        assert serialized["skills"] is None

    def test_serialize_truncates_description(self, service):
        """Test that long descriptions are truncated."""
        long_description = "A" * 2000
        result = SearchResult(
            source="board",
            source_id="1",
            title="Developer",
            company="Corp",
            description=long_description,
            url="https://example.com",
            location="Remote",
            remote=True,
        )

        serialized = service._serialize_result(result)

        assert len(serialized["description"]) == 500
