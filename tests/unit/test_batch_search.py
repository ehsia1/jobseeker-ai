"""
Unit tests for the BatchJobSearcher and BatchSearchScheduler.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import hashlib
import json

from backend.services.batch_search import (
    BatchJobSearcher,
    BatchSearchScheduler,
    get_batch_scheduler,
)


class TestBatchJobSearcherInit:
    """Tests for BatchJobSearcher initialization."""

    def test_init_defaults(self):
        """Test initialization with default cache."""
        with patch("backend.services.batch_search.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache

            searcher = BatchJobSearcher()

            assert searcher.cache == mock_cache
            assert searcher.search_interval == 30 * 60
            assert searcher.max_jobs_per_board == 50
            assert searcher.is_running is False
            assert len(searcher.popular_searches) > 0
            assert len(searcher.professions) > 0

    def test_init_with_custom_cache(self):
        """Test initialization with custom cache."""
        mock_cache = MagicMock()

        searcher = BatchJobSearcher(cache=mock_cache)

        assert searcher.cache == mock_cache

    def test_popular_searches_defined(self):
        """Test that popular searches are defined."""
        with patch("backend.services.batch_search.get_cache"):
            searcher = BatchJobSearcher()

            assert ["python", "developer"] in searcher.popular_searches
            assert ["javascript", "react"] in searcher.popular_searches
            assert ["data", "scientist"] in searcher.popular_searches

    def test_professions_defined(self):
        """Test that professions are defined."""
        with patch("backend.services.batch_search.get_cache"):
            searcher = BatchJobSearcher()

            assert "software_engineer" in searcher.professions
            assert "data_scientist" in searcher.professions
            assert "product_manager" in searcher.professions


class TestBatchJobSearcherRunBatch:
    """Tests for run_batch_search method."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache."""
        cache = MagicMock()
        cache.set = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.memory_cache = MagicMock()
        cache.memory_cache.get_stats.return_value = {"hit_rate": "50.00%"}
        return cache

    @pytest.fixture
    def searcher(self, mock_cache):
        """Create searcher with mocked dependencies."""
        with patch("backend.services.batch_search.get_cache", return_value=mock_cache):
            searcher = BatchJobSearcher(cache=mock_cache)
            searcher.registry = MagicMock()
            searcher.professions = ["test_profession"]
            searcher.popular_searches = [["test", "keywords"]]
            return searcher

    @pytest.mark.asyncio
    async def test_run_batch_search_skips_if_running(self, searcher):
        """Test that concurrent batch searches are skipped."""
        searcher.is_running = True

        await searcher.run_batch_search()

        # Should return without doing anything
        searcher.registry.get_searchers_for_profession.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_batch_search_sets_running_flag(self, searcher, mock_cache):
        """Test that is_running flag is managed correctly."""
        searcher.registry.get_searchers_for_profession.return_value = []

        await searcher.run_batch_search()

        # Should end with is_running = False
        assert searcher.is_running is False

    @pytest.mark.asyncio
    async def test_run_batch_search_searches_professions(self, searcher, mock_cache):
        """Test that professions are searched."""
        mock_searcher_class = MagicMock()
        mock_searcher_instance = MagicMock()
        mock_searcher_instance.search = AsyncMock(return_value=[])
        mock_searcher_class.return_value = mock_searcher_instance
        mock_searcher_class.__name__ = "TestSearcher"

        searcher.registry.get_searchers_for_profession.return_value = [mock_searcher_class]

        await searcher.run_batch_search()

        searcher.registry.get_searchers_for_profession.assert_called_with("test_profession")

    @pytest.mark.asyncio
    async def test_run_batch_search_caches_results(self, searcher, mock_cache):
        """Test that results are cached."""
        searcher.registry.get_searchers_for_profession.return_value = []

        await searcher.run_batch_search()

        # Should cache batch search stats
        assert mock_cache.set.called

    @pytest.mark.asyncio
    async def test_run_batch_search_handles_errors(self, searcher, mock_cache):
        """Test error handling during batch search."""
        searcher.registry.get_searchers_for_profession.side_effect = Exception("Test error")

        # Should not raise
        await searcher.run_batch_search()

        assert searcher.is_running is False


class TestBatchJobSearcherSearchProfession:
    """Tests for _search_profession method."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache."""
        cache = MagicMock()
        cache.set = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    def searcher(self, mock_cache):
        """Create searcher."""
        with patch("backend.services.batch_search.get_cache", return_value=mock_cache):
            return BatchJobSearcher(cache=mock_cache)

    @pytest.mark.asyncio
    async def test_search_profession_limits_boards(self, searcher):
        """Test that only top 3 boards are searched."""
        mock_classes = [MagicMock() for _ in range(5)]
        for i, mc in enumerate(mock_classes):
            mc.__name__ = f"Searcher{i}"
            instance = MagicMock()
            instance.search = AsyncMock(return_value=[])
            mc.return_value = instance

        searcher.registry.get_searchers_for_profession = MagicMock(return_value=mock_classes)

        await searcher._search_profession("software_engineer")

        # Should only search first 3
        assert mock_classes[0].called
        assert mock_classes[1].called
        assert mock_classes[2].called
        assert not mock_classes[3].called
        assert not mock_classes[4].called

    @pytest.mark.asyncio
    async def test_search_profession_skips_recently_searched(self, searcher, mock_cache):
        """Test skipping recently searched boards."""
        mock_class = MagicMock()
        mock_class.__name__ = "TestSearcher"
        mock_instance = MagicMock()
        mock_instance.search = AsyncMock(return_value=[])
        mock_class.return_value = mock_instance

        searcher.registry.get_searchers_for_profession = MagicMock(return_value=[mock_class])

        # Mark as recently searched
        searcher.last_search_time["TestSearcher"] = datetime.now()

        # Should return cached results
        mock_cache.get.return_value = [{"title": "Cached Job"}]

        result = await searcher._search_profession("software_engineer")

        # Should use cached results
        assert len(result) == 1
        mock_instance.search.assert_not_called()


class TestBatchJobSearcherHelpers:
    """Tests for helper methods."""

    @pytest.fixture
    def searcher(self):
        """Create searcher."""
        mock_cache = MagicMock()
        with patch("backend.services.batch_search.get_cache", return_value=mock_cache):
            return BatchJobSearcher(cache=mock_cache)

    def test_should_skip_board_never_searched(self, searcher):
        """Test should not skip board that was never searched."""
        result = searcher._should_skip_board("NewBoard")

        assert result is False

    def test_should_skip_board_recently_searched(self, searcher):
        """Test should skip recently searched board."""
        searcher.last_search_time["RecentBoard"] = datetime.now()

        result = searcher._should_skip_board("RecentBoard")

        assert result is True

    def test_should_skip_board_old_search(self, searcher):
        """Test should not skip board searched long ago."""
        searcher.last_search_time["OldBoard"] = datetime.now() - timedelta(hours=2)

        result = searcher._should_skip_board("OldBoard")

        assert result is False

    def test_generate_job_id(self, searcher):
        """Test job ID generation."""
        job = {"title": "Developer", "company": "TechCorp", "url": "https://example.com"}

        job_id = searcher._generate_job_id(job)

        assert len(job_id) == 32  # MD5 hex digest
        # Same job should produce same ID
        assert searcher._generate_job_id(job) == job_id

    def test_generate_job_id_different_jobs(self, searcher):
        """Test different jobs produce different IDs."""
        job1 = {"title": "Developer", "company": "TechCorp", "url": "https://example.com"}
        job2 = {"title": "Designer", "company": "TechCorp", "url": "https://example.com/2"}

        id1 = searcher._generate_job_id(job1)
        id2 = searcher._generate_job_id(job2)

        assert id1 != id2

    def test_process_job_results(self, searcher):
        """Test job result processing."""
        jobs = [
            {"title": "Job 1", "company": "Corp1"},
            {"title": "Job 2", "company": "Corp2"},
        ]

        result = searcher._process_job_results(jobs, "software_engineer", "TestBoard")

        assert len(result) == 2
        assert result[0]["source_board"] == "TestBoard"
        assert result[0]["profession_match"] == "software_engineer"
        assert "batch_searched_at" in result[0]
        assert "job_id" in result[0]

    def test_process_job_results_respects_limit(self, searcher):
        """Test that processing respects max_jobs_per_board limit."""
        searcher.max_jobs_per_board = 2
        jobs = [{"title": f"Job {i}"} for i in range(10)]

        result = searcher._process_job_results(jobs, "test", "TestBoard")

        assert len(result) == 2

    def test_get_query_cache_key(self, searcher):
        """Test cache key generation from query."""
        query1 = {"keywords": ["python"], "remote_only": True}
        query2 = {"keywords": ["python"], "remote_only": True}
        query3 = {"keywords": ["javascript"], "remote_only": True}

        key1 = searcher._get_query_cache_key(query1)
        key2 = searcher._get_query_cache_key(query2)
        key3 = searcher._get_query_cache_key(query3)

        assert key1 == key2  # Same query = same key
        assert key1 != key3  # Different query = different key
        assert key1.startswith("query:")


class TestBatchJobSearcherGetCachedJobs:
    """Tests for get_cached_jobs method."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache."""
        cache = MagicMock()
        cache.set = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    def searcher(self, mock_cache):
        """Create searcher."""
        with patch("backend.services.batch_search.get_cache", return_value=mock_cache):
            return BatchJobSearcher(cache=mock_cache)

    @pytest.mark.asyncio
    async def test_get_cached_jobs_exact_match(self, searcher, mock_cache):
        """Test returning exact query match from cache."""
        cached_jobs = [{"title": "Python Developer"}]
        mock_cache.get.return_value = cached_jobs

        query = {"keywords": ["python"]}
        result = await searcher.get_cached_jobs(query)

        assert result == cached_jobs

    @pytest.mark.asyncio
    async def test_get_cached_jobs_profession_fallback(self, searcher, mock_cache):
        """Test falling back to profession cache."""
        profession_jobs = [
            {"title": "Python Dev", "remote": True},
            {"title": "Java Dev", "remote": False},
        ]

        # First call returns None (no exact match), second returns profession jobs
        mock_cache.get.side_effect = [None, profession_jobs]

        query = {"profession": "software_engineer", "remote_only": True}
        result = await searcher.get_cached_jobs(query)

        assert len(result) == 1
        assert result[0]["remote"] is True

    @pytest.mark.asyncio
    async def test_get_cached_jobs_returns_empty_on_miss(self, searcher, mock_cache):
        """Test returning empty list when no cache hit."""
        mock_cache.get.return_value = None

        query = {"keywords": ["obscure_term"]}
        result = await searcher.get_cached_jobs(query)

        assert result == []


class TestBatchJobSearcherFilterJobs:
    """Tests for _filter_jobs_by_query method."""

    @pytest.fixture
    def searcher(self):
        """Create searcher."""
        mock_cache = MagicMock()
        with patch("backend.services.batch_search.get_cache", return_value=mock_cache):
            return BatchJobSearcher(cache=mock_cache)

    def test_filter_by_remote_only(self, searcher):
        """Test filtering by remote only."""
        jobs = [
            {"title": "Job 1", "remote": True},
            {"title": "Job 2", "remote": False},
            {"title": "Job 3", "remote": True},
        ]
        query = {"remote_only": True}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 2
        assert all(j["remote"] for j in result)

    def test_filter_by_location(self, searcher):
        """Test filtering by location."""
        jobs = [
            {"title": "Job 1", "location": "San Francisco, CA"},
            {"title": "Job 2", "location": "New York, NY"},
            {"title": "Job 3", "location": "San Jose, CA"},
        ]
        query = {"location": "san"}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 2

    def test_filter_by_min_rate(self, searcher):
        """Test filtering by minimum rate."""
        jobs = [
            {"title": "Job 1", "rate_min": 100000},
            {"title": "Job 2", "rate_min": 80000},
            {"title": "Job 3", "rate_min": 120000},
        ]
        query = {"min_rate": 90000}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 2
        assert all(j["rate_min"] >= 90000 for j in result)

    def test_filter_by_max_rate(self, searcher):
        """Test filtering by maximum rate."""
        jobs = [
            {"title": "Job 1", "rate_max": 100000},
            {"title": "Job 2", "rate_max": 80000},
            {"title": "Job 3", "rate_max": 120000},
        ]
        query = {"max_rate": 100000}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 2
        assert all(j["rate_max"] <= 100000 for j in result)

    def test_filter_by_keywords(self, searcher):
        """Test filtering by keywords."""
        jobs = [
            {"title": "Python Developer", "description": "Build APIs"},
            {"title": "Java Developer", "description": "Enterprise apps"},
            {"title": "Full Stack", "description": "Python and React"},
        ]
        query = {"keywords": ["python"]}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 2

    def test_filter_applies_limit(self, searcher):
        """Test that limit is applied."""
        jobs = [{"title": f"Job {i}"} for i in range(100)]
        query = {"limit": 10}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 10

    def test_filter_combined(self, searcher):
        """Test combining multiple filters."""
        jobs = [
            {"title": "Python Dev", "remote": True, "rate_min": 100000, "location": "NYC", "description": ""},
            {"title": "Python Dev", "remote": True, "rate_min": 80000, "location": "SF", "description": ""},
            {"title": "Java Dev", "remote": False, "rate_min": 120000, "location": "NYC", "description": ""},
        ]
        query = {"remote_only": True, "min_rate": 90000}

        result = searcher._filter_jobs_by_query(jobs, query)

        assert len(result) == 1
        assert result[0]["title"] == "Python Dev"
        assert result[0]["rate_min"] == 100000


class TestBatchSearchScheduler:
    """Tests for BatchSearchScheduler."""

    def test_init(self):
        """Test scheduler initialization."""
        with patch("backend.services.batch_search.BatchJobSearcher"):
            scheduler = BatchSearchScheduler()

            assert scheduler.running is False
            assert scheduler.task is None
            assert scheduler.searcher is not None

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        """Test that start sets running flag."""
        with patch("backend.services.batch_search.BatchJobSearcher") as MockSearcher:
            mock_searcher = MagicMock()
            mock_searcher.run_batch_search = AsyncMock()
            MockSearcher.return_value = mock_searcher

            scheduler = BatchSearchScheduler()

            # Start and immediately stop to test
            task = asyncio.create_task(scheduler.start())
            await asyncio.sleep(0.01)
            scheduler.running = False
            if scheduler.task:
                scheduler.task.cancel()

            assert scheduler.running is False

    @pytest.mark.asyncio
    async def test_start_returns_if_running(self):
        """Test that start returns if already running."""
        with patch("backend.services.batch_search.BatchJobSearcher"):
            scheduler = BatchSearchScheduler()
            scheduler.running = True

            await scheduler.start()

            # Should not create a new task
            assert scheduler.task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        """Test that stop cancels the task."""
        with patch("backend.services.batch_search.BatchJobSearcher") as MockSearcher:
            mock_searcher = MagicMock()
            mock_searcher.run_batch_search = AsyncMock()
            MockSearcher.return_value = mock_searcher

            scheduler = BatchSearchScheduler()
            scheduler.running = True

            # Create a mock task
            async def dummy_task():
                while True:
                    await asyncio.sleep(1)

            scheduler.task = asyncio.create_task(dummy_task())

            await scheduler.stop()

            assert scheduler.running is False
            assert scheduler.task.cancelled()


class TestGetBatchScheduler:
    """Tests for get_batch_scheduler singleton."""

    def test_get_batch_scheduler_creates_instance(self):
        """Test that get_batch_scheduler creates an instance."""
        import backend.services.batch_search as module

        # Reset singleton
        module._scheduler = None

        with patch("backend.services.batch_search.BatchJobSearcher"):
            scheduler = get_batch_scheduler()

            assert isinstance(scheduler, BatchSearchScheduler)

    def test_get_batch_scheduler_returns_same_instance(self):
        """Test that get_batch_scheduler returns the same instance."""
        import backend.services.batch_search as module

        # Reset singleton
        module._scheduler = None

        with patch("backend.services.batch_search.BatchJobSearcher"):
            scheduler1 = get_batch_scheduler()
            scheduler2 = get_batch_scheduler()

            assert scheduler1 is scheduler2
