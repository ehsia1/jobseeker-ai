"""
Unit tests for the JDParserService.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4
from decimal import Decimal

from backend.services.jd_parser_service import (
    JDParserService,
    ParsedJD,
    JDParseResult,
)
from backend.services.scoring_service import ScoreBreakdown
from backend.models.user import UserProfile


class TestParsedJD:
    """Tests for ParsedJD dataclass."""

    def test_to_dict_full(self):
        """Test conversion to dictionary with all fields."""
        parsed = ParsedJD(
            title="Senior Python Developer",
            company="TechCorp",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            nice_to_have_skills=["Docker", "AWS"],
            experience_level="senior",
            experience_years_min=5,
            experience_years_max=8,
            compensation_min=140000,
            compensation_max=180000,
            compensation_type="annual",
            location="San Francisco, CA",
            remote=True,
            employment_type="full-time",
            key_requirements=["5+ years Python", "API development"],
            keywords_to_emphasize=["scalable", "microservices"],
            responsibilities=["Build APIs", "Code reviews"],
            benefits=["Remote work", "Health insurance"],
            raw_text="Full job description...",
        )

        result = parsed.to_dict()

        assert result["title"] == "Senior Python Developer"
        assert result["company"] == "TechCorp"
        assert "Python" in result["required_skills"]
        assert result["remote"] is True
        assert result["compensation_min"] == 140000

    def test_to_dict_minimal(self):
        """Test conversion with minimal data."""
        parsed = ParsedJD(title="Developer")

        result = parsed.to_dict()

        assert result["title"] == "Developer"
        assert result["required_skills"] == []
        assert result["remote"] is False

    def test_default_values(self):
        """Test default values are set correctly."""
        parsed = ParsedJD()

        assert parsed.title is None
        assert parsed.required_skills == []
        assert parsed.nice_to_have_skills == []
        assert parsed.remote is False
        assert parsed.raw_text == ""


class TestJDParseResult:
    """Tests for JDParseResult dataclass."""

    def test_to_dict_without_score(self):
        """Test conversion without match score."""
        parsed = ParsedJD(title="Developer", company="TechCorp")
        result = JDParseResult(parsed=parsed)

        result_dict = result.to_dict()

        assert "parsed" in result_dict
        assert result_dict["parsed"]["title"] == "Developer"
        assert "match_score" not in result_dict
        assert "explanation" not in result_dict

    def test_to_dict_with_score(self):
        """Test conversion with match score."""
        parsed = ParsedJD(title="Developer")
        score = ScoreBreakdown(
            total_score=85.0,
            semantic_similarity=80.0,
            skill_match=90.0,
            experience_match=85.0,
            compensation_match=80.0,
            location_match=100.0,
            freshness_score=90.0,
            preference_match=75.0,
        )
        result = JDParseResult(
            parsed=parsed,
            match_score=score,
            explanation="Strong match for this position.",
        )

        result_dict = result.to_dict()

        assert "match_score" in result_dict
        assert result_dict["match_score"]["total_score"] == 85.0
        assert result_dict["explanation"] == "Strong match for this position."


class TestJDParserService:
    """Tests for JDParserService."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock = MagicMock()
        mock.generate_structured = AsyncMock(
            return_value={
                "title": "Senior Python Developer",
                "company": "TechCorp",
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                "nice_to_have_skills": ["Docker", "AWS"],
                "experience_level": "senior",
                "experience_years_min": 5,
                "experience_years_max": None,
                "compensation_min": 140000,
                "compensation_max": 180000,
                "compensation_type": "annual",
                "location": "San Francisco, CA",
                "remote": True,
                "employment_type": "full-time",
                "key_requirements": ["5+ years Python experience"],
                "keywords_to_emphasize": ["scalable", "microservices"],
                "responsibilities": ["Build APIs", "Lead projects"],
                "benefits": ["Remote work", "Equity"],
            }
        )
        return mock

    @pytest.fixture
    def parser_service(self, mock_llm_service):
        """Create parser service with mocked LLM."""
        return JDParserService(db=None, llm_service=mock_llm_service)

    @pytest.fixture
    def sample_jd_text(self):
        """Sample job description text."""
        return """
        Senior Python Developer

        Company: TechCorp Inc.
        Location: San Francisco, CA (Remote OK)
        Salary: $140,000 - $180,000/year

        About the Role:
        We're looking for a Senior Python Developer to join our team.

        Requirements:
        - 5+ years of Python experience
        - Experience with FastAPI or Django
        - PostgreSQL knowledge

        Nice to Have:
        - Docker experience
        - AWS familiarity

        Responsibilities:
        - Build scalable APIs
        - Lead technical projects

        Benefits:
        - Remote work options
        - Competitive equity package
        """

    @pytest.mark.asyncio
    async def test_parse_success(self, parser_service, sample_jd_text, mock_llm_service):
        """Test successful JD parsing."""
        result = await parser_service.parse(sample_jd_text)

        assert isinstance(result, ParsedJD)
        assert result.title == "Senior Python Developer"
        assert result.company == "TechCorp"
        assert "Python" in result.required_skills
        assert result.remote is True
        assert result.raw_text == sample_jd_text
        mock_llm_service.generate_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_empty_text_raises_error(self, parser_service):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Job description text cannot be empty"):
            await parser_service.parse("")

    @pytest.mark.asyncio
    async def test_parse_whitespace_only_raises_error(self, parser_service):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="Job description text cannot be empty"):
            await parser_service.parse("   \n\t   ")

    @pytest.mark.asyncio
    async def test_parse_llm_error_propagates(self, parser_service, mock_llm_service):
        """Test that LLM errors are propagated."""
        mock_llm_service.generate_structured = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        with pytest.raises(Exception, match="LLM service unavailable"):
            await parser_service.parse("Valid job description text")

    @pytest.mark.asyncio
    async def test_parse_and_score_without_profile(
        self, parser_service, sample_jd_text
    ):
        """Test parsing without profile returns no score."""
        result = await parser_service.parse_and_score(sample_jd_text)

        assert isinstance(result, JDParseResult)
        assert result.parsed.title == "Senior Python Developer"
        assert result.match_score is None
        assert result.explanation is None

    @pytest.mark.asyncio
    async def test_parse_and_score_with_profile(
        self, parser_service, sample_jd_text, mock_embedding_service
    ):
        """Test parsing with profile returns score."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
        profile.experience_years = 6
        profile.min_rate_usd = Decimal("130000")
        profile.preferences = {"remote_only": True}
        profile.profile_embedding = None

        result = await parser_service.parse_and_score(
            sample_jd_text,
            profile=profile,
        )

        assert isinstance(result, JDParseResult)
        assert result.parsed is not None
        assert result.match_score is not None
        assert result.explanation is not None

    @pytest.mark.asyncio
    async def test_extract_keywords(self, parser_service, mock_llm_service):
        """Test keyword extraction."""
        mock_llm_service.generate_structured = AsyncMock(
            return_value=[
                "Python",
                "FastAPI",
                "scalable",
                "microservices",
                "leadership",
            ]
        )

        result = await parser_service.extract_keywords("Job description text")

        assert isinstance(result, list)
        assert "Python" in result
        assert "FastAPI" in result

    @pytest.mark.asyncio
    async def test_extract_keywords_handles_non_list_response(
        self, parser_service, mock_llm_service
    ):
        """Test keyword extraction handles non-list response."""
        mock_llm_service.generate_structured = AsyncMock(
            return_value={"error": "not a list"}
        )

        result = await parser_service.extract_keywords("Job description text")

        assert result == []

    @pytest.mark.asyncio
    async def test_extract_keywords_handles_error(
        self, parser_service, mock_llm_service
    ):
        """Test keyword extraction handles errors gracefully."""
        mock_llm_service.generate_structured = AsyncMock(
            side_effect=Exception("Error")
        )

        result = await parser_service.extract_keywords("Job description text")

        assert result == []

    def test_create_pseudo_job(self, parser_service):
        """Test pseudo job creation from parsed JD."""
        parsed = ParsedJD(
            title="Senior Developer",
            company="TestCorp",
            required_skills=["Python", "AWS"],
            experience_level="senior",
            experience_years_min=5,
            compensation_min=120000,
            compensation_max=150000,
            compensation_type="annual",
            location="Remote",
            remote=True,
            employment_type="full-time",
            key_requirements=["5+ years experience"],
            raw_text="Job description text",
        )

        pseudo_job = parser_service._create_pseudo_job(parsed)

        assert pseudo_job.title == "Senior Developer"
        assert pseudo_job.company == "TestCorp"
        assert pseudo_job.skills == ["Python", "AWS"]
        assert pseudo_job.rate_min == 120000
        assert pseudo_job.rate_max == 150000
        assert pseudo_job.remote is True
        assert pseudo_job.requirements["experience_level"] == "senior"

    def test_create_pseudo_job_with_missing_title(self, parser_service):
        """Test pseudo job with missing title defaults to 'Unknown Position'."""
        parsed = ParsedJD(title=None, company="TestCorp")

        pseudo_job = parser_service._create_pseudo_job(parsed)

        assert pseudo_job.title == "Unknown Position"

    def test_system_prompt_defined(self, parser_service):
        """Test that system prompt is properly defined."""
        assert parser_service.PARSE_SYSTEM_PROMPT
        assert "job description" in parser_service.PARSE_SYSTEM_PROMPT.lower()
        assert "skills" in parser_service.PARSE_SYSTEM_PROMPT.lower()


class TestJDParserServiceWithDB:
    """Tests for JDParserService with database integration."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def parser_service_with_db(self, mock_db, mock_llm_service):
        """Create parser service with mock DB."""
        mock_llm = MagicMock()
        mock_llm.generate_structured = AsyncMock(
            return_value={
                "title": "Developer",
                "company": "Corp",
                "required_skills": [],
                "nice_to_have_skills": [],
                "experience_level": None,
                "remote": False,
                "key_requirements": [],
                "keywords_to_emphasize": [],
                "responsibilities": [],
                "benefits": [],
            }
        )
        return JDParserService(db=mock_db, llm_service=mock_llm)

    @pytest.mark.asyncio
    async def test_get_user_profile_success(
        self, parser_service_with_db, mock_db
    ):
        """Test fetching user profile from DB."""
        user_id = uuid4()
        expected_profile = MagicMock(spec=UserProfile)
        expected_profile.skills = ["Python"]

        mock_db.execute.return_value.scalar_one_or_none.return_value = expected_profile

        result = await parser_service_with_db._get_user_profile(user_id)

        assert result == expected_profile

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(
        self, parser_service_with_db, mock_db
    ):
        """Test handling missing user profile."""
        user_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await parser_service_with_db._get_user_profile(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_profile_db_error(
        self, parser_service_with_db, mock_db
    ):
        """Test handling DB errors gracefully."""
        user_id = uuid4()
        mock_db.execute.side_effect = Exception("DB connection error")

        result = await parser_service_with_db._get_user_profile(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_profile_no_db(self):
        """Test handling when no DB is provided."""
        service = JDParserService(db=None, llm_service=MagicMock())
        user_id = uuid4()

        result = await service._get_user_profile(user_id)

        assert result is None


class TestParsedJDFieldValidation:
    """Tests for ParsedJD field validation and edge cases."""

    def test_experience_years_range(self):
        """Test experience years min/max relationship."""
        parsed = ParsedJD(
            experience_years_min=3,
            experience_years_max=5,
        )

        assert parsed.experience_years_min == 3
        assert parsed.experience_years_max == 5

    def test_compensation_range(self):
        """Test compensation min/max values."""
        parsed = ParsedJD(
            compensation_min=100000.0,
            compensation_max=150000.0,
            compensation_type="annual",
        )

        assert parsed.compensation_min == 100000.0
        assert parsed.compensation_max == 150000.0

    def test_hourly_compensation(self):
        """Test hourly compensation type."""
        parsed = ParsedJD(
            compensation_min=75.0,
            compensation_max=100.0,
            compensation_type="hourly",
        )

        assert parsed.compensation_type == "hourly"
        assert parsed.compensation_min == 75.0

    def test_experience_levels(self):
        """Test various experience levels."""
        for level in ["junior", "mid", "senior", "lead", "principal"]:
            parsed = ParsedJD(experience_level=level)
            assert parsed.experience_level == level

    def test_employment_types(self):
        """Test various employment types."""
        for emp_type in ["full-time", "part-time", "contract", "freelance"]:
            parsed = ParsedJD(employment_type=emp_type)
            assert parsed.employment_type == emp_type
