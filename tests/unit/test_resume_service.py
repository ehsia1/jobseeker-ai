"""
Unit tests for the ResumeService.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from backend.services.resume_service import ResumeService
from backend.models.resume import Resume, WorkExperience


class TestResumeService:
    """Tests for ResumeService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.flush = AsyncMock()
        mock.refresh = AsyncMock()
        mock.delete = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def resume_service(self, mock_db, mock_llm_service):
        """Create resume service with mocked dependencies."""
        return ResumeService(db=mock_db, llm_service=mock_llm_service)

    @pytest.fixture
    def sample_parsed_data(self):
        """Sample parsed resume data from LLM."""
        return {
            "full_name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "(555) 123-4567",
            "location": "San Francisco, CA",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "github_url": "https://github.com/johndoe",
            "portfolio_url": "https://johndoe.dev",
            "summary": "Senior Software Engineer with 8+ years of experience.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "AWS", "Docker"],
            "certifications": ["AWS Solutions Architect"],
            "languages": ["English", "Spanish"],
            "education": [
                {
                    "degree": "B.S. Computer Science",
                    "field": "Computer Science",
                    "school": "Stanford University",
                    "year": "2017",
                    "gpa": "3.8",
                }
            ],
            "work_experiences": [
                {
                    "company": "TechCorp Inc.",
                    "title": "Senior Software Engineer",
                    "location": "San Francisco, CA",
                    "employment_type": "full-time",
                    "is_remote": False,
                    "start_date": "2020-01-01",
                    "end_date": None,
                    "is_current": True,
                    "description": "Led development of microservices architecture.",
                    "achievements": [
                        "Reduced API response time by 60%",
                        "Mentored team of 5 junior developers",
                    ],
                    "skills_used": ["Python", "FastAPI", "PostgreSQL"],
                    "metrics": {"users_served": "1M+"},
                },
                {
                    "company": "StartupXYZ",
                    "title": "Software Engineer",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "is_remote": True,
                    "start_date": "2017-06",
                    "end_date": "2019-12",
                    "is_current": False,
                    "description": "Built real-time data processing pipeline.",
                    "achievements": ["Handled 10K events/second"],
                    "skills_used": ["Python", "Django", "Celery"],
                    "metrics": {},
                },
            ],
            "parse_quality_score": 85,
        }

    @pytest.mark.asyncio
    async def test_upload_and_parse_new_resume(
        self, resume_service, mock_db, mock_llm_service, sample_parsed_data
    ):
        """Test uploading and parsing a new resume."""
        user_id = uuid4()
        file_content = b"Sample resume text content with more than 50 characters for validation."
        file_name = "resume.txt"
        file_type = "txt"

        # Setup mocks
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_llm_service.generate_structured = AsyncMock(return_value=sample_parsed_data)

        result = await resume_service.upload_and_parse(
            user_id, file_content, file_name, file_type
        )

        assert isinstance(result, Resume)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_and_parse_updates_existing_resume(
        self, resume_service, mock_db, mock_llm_service, sample_parsed_data
    ):
        """Test that uploading updates an existing resume."""
        user_id = uuid4()
        existing_resume = Resume(
            id=uuid4(),
            user_id=user_id,
            file_type="txt",
            raw_text="Old resume content",
        )
        existing_resume.work_experiences = []

        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_resume
        mock_llm_service.generate_structured = AsyncMock(return_value=sample_parsed_data)

        file_content = b"New resume content with more than 50 characters for validation."
        result = await resume_service.upload_and_parse(
            user_id, file_content, "new_resume.txt", "txt"
        )

        assert result.id == existing_resume.id
        assert result.file_name == "new_resume.txt"
        # Should not add new resume
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_and_parse_short_text_raises_error(self, resume_service):
        """Test that short/empty text raises ValueError."""
        user_id = uuid4()
        file_content = b"Short"

        with pytest.raises(ValueError, match="Could not extract meaningful text"):
            await resume_service.upload_and_parse(
                user_id, file_content, "resume.txt", "txt"
            )

    @pytest.mark.asyncio
    async def test_parse_text_creates_resume(
        self, resume_service, mock_db, mock_llm_service, sample_parsed_data
    ):
        """Test parsing resume from pasted text."""
        user_id = uuid4()
        text = "Full resume text content with all the details needed for parsing."

        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_llm_service.generate_structured = AsyncMock(return_value=sample_parsed_data)

        result = await resume_service.parse_text(user_id, text)

        assert isinstance(result, Resume)
        assert result.file_type == "text"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_text_short_text_raises_error(self, resume_service):
        """Test that short text raises ValueError."""
        user_id = uuid4()

        with pytest.raises(ValueError, match="Resume text is too short"):
            await resume_service.parse_text(user_id, "Short")

    @pytest.mark.asyncio
    async def test_get_resume(self, resume_service, mock_db):
        """Test getting a user's resume."""
        user_id = uuid4()
        expected_resume = Resume(id=uuid4(), user_id=user_id, file_type="txt")

        mock_db.execute.return_value.scalar_one_or_none.return_value = expected_resume

        result = await resume_service.get_resume(user_id)

        assert result == expected_resume

    @pytest.mark.asyncio
    async def test_get_resume_not_found(self, resume_service, mock_db):
        """Test getting resume when none exists."""
        user_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await resume_service.get_resume(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_resume_success(self, resume_service, mock_db):
        """Test deleting an existing resume."""
        user_id = uuid4()
        existing_resume = Resume(id=uuid4(), user_id=user_id, file_type="txt")

        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_resume

        result = await resume_service.delete_resume(user_id)

        assert result is True
        mock_db.delete.assert_called_once_with(existing_resume)

    @pytest.mark.asyncio
    async def test_delete_resume_not_found(self, resume_service, mock_db):
        """Test deleting non-existent resume."""
        user_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await resume_service.delete_resume(user_id)

        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_relevant_experience(self, resume_service, mock_db):
        """Test getting relevant work experiences."""
        user_id = uuid4()

        # Create mock resume with work experiences
        resume = MagicMock(spec=Resume)
        exp1 = MagicMock(spec=WorkExperience)
        exp1.skills_used = ["Python", "FastAPI", "PostgreSQL"]
        exp1.description = "Built APIs"
        exp1.achievements = ["Improved performance"]

        exp2 = MagicMock(spec=WorkExperience)
        exp2.skills_used = ["JavaScript", "React"]
        exp2.description = "Frontend development"
        exp2.achievements = ["Built UI components"]

        resume.work_experiences = [exp1, exp2]

        mock_db.execute.return_value.scalar_one_or_none.return_value = resume

        result = await resume_service.get_relevant_experience(
            user_id,
            required_skills=["Python", "FastAPI"],
            nice_to_have_skills=["AWS"],
            limit=2,
        )

        # Python/FastAPI experience should be first (higher relevance)
        assert len(result) <= 2
        assert exp1 in result

    @pytest.mark.asyncio
    async def test_get_relevant_experience_no_resume(self, resume_service, mock_db):
        """Test relevant experience when no resume exists."""
        user_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await resume_service.get_relevant_experience(
            user_id, required_skills=["Python"]
        )

        assert result == []


class TestResumeTextExtraction:
    """Tests for text extraction methods."""

    @pytest.fixture
    def resume_service(self, mock_llm_service):
        """Create resume service."""
        mock_db = MagicMock()
        return ResumeService(db=mock_db, llm_service=mock_llm_service)

    @pytest.mark.asyncio
    async def test_extract_text_from_txt(self, resume_service):
        """Test extracting text from plain text file."""
        content = b"This is plain text resume content."

        result = await resume_service._extract_text(content, "txt")

        assert result == "This is plain text resume content."

    @pytest.mark.asyncio
    async def test_extract_text_from_text_mime(self, resume_service):
        """Test extracting text from text/plain MIME type."""
        content = b"Resume content here."

        result = await resume_service._extract_text(content, "text/plain")

        assert result == "Resume content here."

    def test_normalize_file_type_pdf(self, resume_service):
        """Test normalizing PDF file types."""
        assert resume_service._normalize_file_type("pdf") == "pdf"
        assert resume_service._normalize_file_type("application/pdf") == "pdf"
        assert resume_service._normalize_file_type("PDF") == "pdf"

    def test_normalize_file_type_docx(self, resume_service):
        """Test normalizing DOCX file types."""
        assert resume_service._normalize_file_type("docx") == "docx"
        assert (
            resume_service._normalize_file_type(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            == "docx"
        )

    def test_normalize_file_type_txt(self, resume_service):
        """Test normalizing text file types."""
        assert resume_service._normalize_file_type("txt") == "txt"
        assert resume_service._normalize_file_type("text/plain") == "txt"


class TestResumeParsing:
    """Tests for resume parsing methods."""

    @pytest.fixture
    def resume_service(self, mock_llm_service):
        """Create resume service."""
        mock_db = MagicMock()
        return ResumeService(db=mock_db, llm_service=mock_llm_service)

    def test_parse_date_full_iso(self, resume_service):
        """Test parsing full ISO date."""
        result = resume_service._parse_date("2023-06-15")

        assert result == date(2023, 6, 15)

    def test_parse_date_year_month(self, resume_service):
        """Test parsing year-month date."""
        result = resume_service._parse_date("2023-06")

        assert result == date(2023, 6, 1)

    def test_parse_date_year_only(self, resume_service):
        """Test parsing year only."""
        result = resume_service._parse_date("2023")

        assert result == date(2023, 1, 1)

    def test_parse_date_none(self, resume_service):
        """Test parsing None date."""
        result = resume_service._parse_date(None)

        assert result is None

    def test_parse_date_invalid(self, resume_service):
        """Test parsing invalid date."""
        result = resume_service._parse_date("not-a-date")

        assert result is None

    def test_extract_skills_fallback(self, resume_service):
        """Test fallback skill extraction."""
        text = "I have 5 years experience with Python and Django. Also worked with React and AWS."

        result = resume_service._extract_skills_fallback(text)

        assert "Python" in result
        assert "Django" in result
        assert "React" in result
        assert "AWS" in result

    def test_extract_skills_fallback_empty_text(self, resume_service):
        """Test fallback extraction with no skills."""
        text = "I am a great worker and team player."

        result = resume_service._extract_skills_fallback(text)

        assert isinstance(result, list)

    def test_apply_parsed_data(self, resume_service, sample_parsed_data):
        """Test applying parsed data to resume object."""
        resume = Resume(user_id=uuid4(), file_type="text", raw_text="test")
        resume.work_experiences = []

        # Use fixture data
        parsed_data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "location": "NYC",
            "skills": ["Python", "AWS"],
            "certifications": ["AWS Certified"],
            "languages": ["English"],
            "education": [{"degree": "BS", "school": "MIT", "year": "2020"}],
            "work_experiences": [
                {
                    "company": "TechCorp",
                    "title": "Engineer",
                    "start_date": "2020-01",
                    "end_date": None,
                    "is_current": True,
                    "description": "Built stuff",
                    "achievements": ["Did things"],
                    "skills_used": ["Python"],
                }
            ],
            "parse_quality_score": 90,
        }

        resume_service._apply_parsed_data(resume, parsed_data)

        assert resume.full_name == "John Doe"
        assert resume.email == "john@example.com"
        assert resume.skills == ["Python", "AWS"]
        assert resume.parse_quality_score == 90
        assert len(resume.work_experiences) == 1
        assert resume.work_experiences[0].company == "TechCorp"

    @pytest.fixture
    def sample_parsed_data(self):
        """Sample parsed data for tests."""
        return {
            "full_name": "John Doe",
            "email": "john@example.com",
            "skills": ["Python"],
            "work_experiences": [],
            "parse_quality_score": 85,
        }


class TestLLMParsing:
    """Tests for LLM parsing integration."""

    @pytest.fixture
    def resume_service(self, mock_llm_service):
        """Create resume service."""
        mock_db = MagicMock()
        return ResumeService(db=mock_db, llm_service=mock_llm_service)

    @pytest.mark.asyncio
    async def test_parse_with_llm_success(self, resume_service, mock_llm_service):
        """Test successful LLM parsing."""
        mock_llm_service.generate_structured = AsyncMock(
            return_value={
                "full_name": "Test User",
                "skills": ["Python", "AWS"],
                "parse_quality_score": 90,
            }
        )

        result = await resume_service._parse_with_llm("Resume text here")

        assert result["full_name"] == "Test User"
        assert "Python" in result["skills"]
        mock_llm_service.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_with_llm_fallback_on_error(
        self, resume_service, mock_llm_service
    ):
        """Test fallback parsing when LLM fails."""
        mock_llm_service.generate_structured = AsyncMock(
            side_effect=Exception("LLM error")
        )

        result = await resume_service._parse_with_llm(
            "Resume with Python and AWS experience"
        )

        # Should return fallback with extracted skills
        assert "skills" in result
        assert result["parse_quality_score"] == 20
