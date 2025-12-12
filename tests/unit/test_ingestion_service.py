"""
Unit tests for the IngestionService.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from backend.services.ingestion_service import IngestionService
from backend.models.job import Job


class TestIngestionServiceInit:
    """Tests for IngestionService initialization."""

    def test_init(self):
        """Test service initialization."""
        mock_db = MagicMock()

        with patch("backend.services.ingestion_service.UpworkEmailParser") as MockUpwork:
            with patch("backend.services.ingestion_service.RemoteOKParser") as MockRemoteOK:
                MockUpwork.return_value = MagicMock()
                MockRemoteOK.return_value = MagicMock()

                service = IngestionService(db=mock_db)

                assert service.db == mock_db
                assert len(service.email_parsers) > 0
                assert len(service.rss_parsers) > 0


class TestIngestAllSources:
    """Tests for ingest_all_sources method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mocked parsers."""
        with patch("backend.services.ingestion_service.UpworkEmailParser") as MockUpwork:
            with patch("backend.services.ingestion_service.RemoteOKParser") as MockRemoteOK:
                mock_email_parser = MagicMock()
                mock_email_parser.source_name = "upwork"
                mock_email_parser.fetch_emails = AsyncMock(return_value=[])
                mock_email_parser.parse = AsyncMock(return_value=[])
                MockUpwork.return_value = mock_email_parser

                mock_rss_parser = MagicMock()
                mock_rss_parser.source_name = "remoteok"
                mock_rss_parser.feed_url = "https://remoteok.com/remote-jobs.rss"
                mock_rss_parser.fetch_and_parse = AsyncMock(return_value=[])
                mock_rss_parser.__aenter__ = AsyncMock(return_value=mock_rss_parser)
                mock_rss_parser.__aexit__ = AsyncMock(return_value=None)
                MockRemoteOK.return_value = mock_rss_parser

                return IngestionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_ingest_all_sources_success(self, service):
        """Test successful ingestion from all sources."""
        result = await service.ingest_all_sources()

        assert "email_results" in result
        assert "rss_results" in result
        assert "total_jobs" in result
        assert "errors" in result
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_ingest_all_sources_with_limit(self, service):
        """Test ingestion with custom limit."""
        result = await service.ingest_all_sources(limit_per_source=25)

        assert result["total_jobs"] >= 0

    @pytest.mark.asyncio
    async def test_ingest_all_sources_handles_email_error(self, service):
        """Test handling errors from email parser."""
        service.email_parsers[0].fetch_emails = AsyncMock(
            side_effect=Exception("Email error")
        )

        result = await service.ingest_all_sources()

        assert len(result["errors"]) > 0
        assert "Email error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_ingest_all_sources_handles_rss_error(self, service):
        """Test handling errors from RSS parser."""
        service.rss_parsers[0].__aenter__ = AsyncMock(
            side_effect=Exception("RSS error")
        )

        result = await service.ingest_all_sources()

        assert len(result["errors"]) > 0
        assert "RSS error" in result["errors"][0]


class TestIngestFromEmailParser:
    """Tests for _ingest_from_email_parser method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.execute = AsyncMock()
        mock.execute.return_value.scalar_one_or_none.return_value = None
        return mock

    @pytest.fixture
    def mock_parser(self):
        """Create mock email parser."""
        parser = MagicMock()
        parser.source_name = "test_parser"
        return parser

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        with patch("backend.services.ingestion_service.UpworkEmailParser"):
            with patch("backend.services.ingestion_service.RemoteOKParser"):
                return IngestionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_ingest_from_email_parser_success(self, service, mock_db, mock_parser):
        """Test successful email parsing."""
        mock_parser.fetch_emails = AsyncMock(
            return_value=[
                {
                    "subject": "New Job",
                    "from": "upwork@upwork.com",
                    "body": "Job description",
                    "date": "2024-01-01",
                }
            ]
        )

        mock_job = MagicMock()
        mock_job.source = "upwork"
        mock_job.source_id = "123"
        mock_job.title = "Python Developer"
        mock_job.company = "TechCorp"
        mock_job.description = "Build APIs"
        mock_job.requirements = []
        mock_job.skills = ["Python"]
        mock_job.rate_min = 50
        mock_job.rate_max = 100
        mock_job.rate_type = "hourly"
        mock_job.location = "Remote"
        mock_job.remote = True
        mock_job.hours_per_week = 40
        mock_job.duration = "3 months"
        mock_job.posted_at = datetime.now()
        mock_job.expires_at = None
        mock_job.url = "https://upwork.com/job/123"
        mock_job.raw_data = {}

        mock_parser.parse = AsyncMock(return_value=[mock_job])

        result = await service._ingest_from_email_parser(mock_parser, limit=10)

        assert result["emails_processed"] == 1
        assert result["jobs_parsed"] == 1
        assert result["source"] == "test_parser"

    @pytest.mark.asyncio
    async def test_ingest_from_email_parser_fetch_error(self, service, mock_parser):
        """Test handling fetch errors."""
        mock_parser.fetch_emails = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await service._ingest_from_email_parser(mock_parser, limit=10)

        assert result["emails_processed"] == 0
        assert result["jobs_parsed"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ingest_from_email_parser_parse_error(self, service, mock_parser):
        """Test handling parse errors for individual emails."""
        mock_parser.fetch_emails = AsyncMock(
            return_value=[
                {"subject": "Job 1", "from": "test@test.com", "body": "body1", "date": "2024-01-01"},
                {"subject": "Job 2", "from": "test@test.com", "body": "body2", "date": "2024-01-01"},
            ]
        )

        # First email parses, second errors
        mock_parser.parse = AsyncMock(
            side_effect=[
                [MagicMock()],
                Exception("Parse error"),
            ]
        )

        # Patch _store_jobs to avoid DB issues
        with patch.object(service, "_store_jobs", AsyncMock(return_value=0)):
            result = await service._ingest_from_email_parser(mock_parser, limit=10)

        assert result["emails_processed"] == 1


class TestIngestFromRSSParser:
    """Tests for _ingest_from_rss_parser method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.execute = AsyncMock()
        mock.execute.return_value.scalar_one_or_none.return_value = None
        return mock

    @pytest.fixture
    def mock_parser(self):
        """Create mock RSS parser."""
        parser = MagicMock()
        parser.source_name = "test_rss"
        parser.feed_url = "https://example.com/feed.rss"
        parser.__aenter__ = AsyncMock(return_value=parser)
        parser.__aexit__ = AsyncMock(return_value=None)
        return parser

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        with patch("backend.services.ingestion_service.UpworkEmailParser"):
            with patch("backend.services.ingestion_service.RemoteOKParser"):
                return IngestionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_ingest_from_rss_parser_success(self, service, mock_parser, mock_db):
        """Test successful RSS parsing."""
        mock_job = MagicMock()
        mock_job.source = "remoteok"
        mock_job.source_id = "456"
        mock_job.title = "React Developer"
        mock_job.company = "StartupXYZ"
        mock_job.description = "Build UI"
        mock_job.requirements = []
        mock_job.skills = ["React"]
        mock_job.rate_min = None
        mock_job.rate_max = None
        mock_job.rate_type = None
        mock_job.location = "Remote"
        mock_job.remote = True
        mock_job.hours_per_week = None
        mock_job.duration = None
        mock_job.posted_at = datetime.now()
        mock_job.expires_at = None
        mock_job.url = "https://remoteok.com/job/456"
        mock_job.raw_data = {}

        mock_parser.fetch_and_parse = AsyncMock(return_value=[mock_job])

        result = await service._ingest_from_rss_parser(mock_parser, limit=10)

        assert result["jobs_parsed"] == 1
        assert result["source"] == "test_rss"
        assert result["feed_url"] == "https://example.com/feed.rss"

    @pytest.mark.asyncio
    async def test_ingest_from_rss_parser_error(self, service, mock_parser):
        """Test handling RSS fetch errors."""
        mock_parser.__aenter__ = AsyncMock(
            side_effect=Exception("Feed unavailable")
        )

        result = await service._ingest_from_rss_parser(mock_parser, limit=10)

        assert result["jobs_parsed"] == 0
        assert "error" in result


class TestStoreJobs:
    """Tests for _store_jobs method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        with patch("backend.services.ingestion_service.UpworkEmailParser"):
            with patch("backend.services.ingestion_service.RemoteOKParser"):
                return IngestionService(db=mock_db)

    @pytest.fixture
    def mock_parsed_job(self):
        """Create mock parsed job."""
        job = MagicMock()
        job.source = "upwork"
        job.source_id = "job123"
        job.title = "Python Developer"
        job.company = "TechCorp"
        job.description = "Build APIs"
        job.requirements = ["5 years experience"]
        job.skills = ["Python", "FastAPI"]
        job.rate_min = 50
        job.rate_max = 100
        job.rate_type = "hourly"
        job.location = "Remote"
        job.remote = True
        job.hours_per_week = 40
        job.duration = "6 months"
        job.posted_at = datetime.now()
        job.expires_at = None
        job.url = "https://upwork.com/job/123"
        job.raw_data = {"original": "data"}
        return job

    @pytest.mark.asyncio
    async def test_store_jobs_empty_list(self, service):
        """Test storing empty job list."""
        result = await service._store_jobs([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_store_jobs_new_job(self, service, mock_db, mock_parsed_job):
        """Test storing new jobs."""
        # No existing job
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service._store_jobs([mock_parsed_job])

        assert result == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_jobs_skip_duplicate(self, service, mock_db, mock_parsed_job):
        """Test skipping duplicate jobs."""
        # Existing job found
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(spec=Job)

        result = await service._store_jobs([mock_parsed_job])

        assert result == 0
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_jobs_rollback_on_error(self, service, mock_db, mock_parsed_job):
        """Test rollback on database error."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.commit.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await service._store_jobs([mock_parsed_job])

        mock_db.rollback.assert_called_once()


class TestFindExistingJob:
    """Tests for _find_existing_job method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        with patch("backend.services.ingestion_service.UpworkEmailParser"):
            with patch("backend.services.ingestion_service.RemoteOKParser"):
                return IngestionService(db=mock_db)

    @pytest.fixture
    def mock_parsed_job(self):
        """Create mock parsed job."""
        job = MagicMock()
        job.source = "upwork"
        job.source_id = "job123"
        job.title = "Python Developer"
        job.company = "TechCorp"
        job.url = "https://upwork.com/job/123"
        return job

    @pytest.mark.asyncio
    async def test_find_by_source_and_id(self, service, mock_db, mock_parsed_job):
        """Test finding job by source and source_id."""
        existing_job = MagicMock(spec=Job)
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_job

        result = await service._find_existing_job(mock_parsed_job)

        assert result == existing_job

    @pytest.mark.asyncio
    async def test_find_by_url(self, service, mock_db, mock_parsed_job):
        """Test finding job by URL when source_id doesn't match."""
        mock_parsed_job.source_id = None

        existing_job = MagicMock(spec=Job)
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_job

        result = await service._find_existing_job(mock_parsed_job)

        assert result == existing_job

    @pytest.mark.asyncio
    async def test_find_by_title_company(self, service, mock_db, mock_parsed_job):
        """Test finding job by title and company."""
        mock_parsed_job.source_id = None
        mock_parsed_job.url = None

        # First two checks return None, third finds match
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # source_id check
            None,  # url check
            MagicMock(spec=Job),  # title+company check
        ]

        # Note: With source_id=None, first check is skipped
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(spec=Job)

        result = await service._find_existing_job(mock_parsed_job)

        assert result is not None

    @pytest.mark.asyncio
    async def test_find_no_match(self, service, mock_db, mock_parsed_job):
        """Test when no matching job is found."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service._find_existing_job(mock_parsed_job)

        assert result is None


class TestTestParsers:
    """Tests for test_parsers method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mocked parsers."""
        with patch("backend.services.ingestion_service.UpworkEmailParser") as MockUpwork:
            with patch("backend.services.ingestion_service.RemoteOKParser") as MockRemoteOK:
                mock_email_parser = MagicMock()
                mock_email_parser.source_name = "upwork"
                MockUpwork.return_value = mock_email_parser

                mock_rss_parser = MagicMock()
                mock_rss_parser.source_name = "remoteok"
                mock_rss_parser.feed_url = "https://remoteok.com/feed.rss"
                MockRemoteOK.return_value = mock_rss_parser

                return IngestionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_test_parsers_all_success(self, service):
        """Test all parsers pass tests."""
        mock_job = MagicMock()
        mock_job.__dict__ = {"title": "Test Job", "company": "TestCorp"}

        # Setup email parser
        service.email_parsers[0].fetch_emails = AsyncMock(
            return_value=[
                {"subject": "Job", "from": "test@test.com", "body": "body", "date": "2024-01-01"}
            ]
        )
        service.email_parsers[0].parse = AsyncMock(return_value=[mock_job])

        # Setup RSS parser
        service.rss_parsers[0].__aenter__ = AsyncMock(return_value=service.rss_parsers[0])
        service.rss_parsers[0].__aexit__ = AsyncMock(return_value=None)
        service.rss_parsers[0].fetch_and_parse = AsyncMock(return_value=[mock_job])

        result = await service.test_parsers()

        assert result["overall_status"] == "success"
        assert result["email_parsers"]["upwork"]["status"] == "success"
        assert result["rss_parsers"]["remoteok"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_test_parsers_partial_failure(self, service):
        """Test partial failure when some parsers fail."""
        # Email parser fails
        service.email_parsers[0].fetch_emails = AsyncMock(
            side_effect=Exception("Email error")
        )

        # RSS parser succeeds
        mock_job = MagicMock()
        mock_job.__dict__ = {"title": "Test Job"}
        service.rss_parsers[0].__aenter__ = AsyncMock(return_value=service.rss_parsers[0])
        service.rss_parsers[0].__aexit__ = AsyncMock(return_value=None)
        service.rss_parsers[0].fetch_and_parse = AsyncMock(return_value=[mock_job])

        result = await service.test_parsers()

        assert result["overall_status"] == "partial_failure"
        assert result["email_parsers"]["upwork"]["status"] == "error"
        assert result["rss_parsers"]["remoteok"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_test_parsers_includes_sample_job(self, service):
        """Test that sample job is included in results."""
        mock_job = MagicMock()
        mock_job.__dict__ = {"title": "Sample Job", "company": "SampleCorp"}

        service.email_parsers[0].fetch_emails = AsyncMock(
            return_value=[
                {"subject": "Job", "from": "test@test.com", "body": "body", "date": "2024-01-01"}
            ]
        )
        service.email_parsers[0].parse = AsyncMock(return_value=[mock_job])

        service.rss_parsers[0].__aenter__ = AsyncMock(return_value=service.rss_parsers[0])
        service.rss_parsers[0].__aexit__ = AsyncMock(return_value=None)
        service.rss_parsers[0].fetch_and_parse = AsyncMock(return_value=[mock_job])

        result = await service.test_parsers()

        assert result["email_parsers"]["upwork"]["sample_job"] is not None
        assert result["rss_parsers"]["remoteok"]["sample_job"] is not None
