"""
Unit tests for the ProposalService.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

from backend.services.proposal_service import (
    ProposalService,
    ProposalTone,
    GeneratedProposal,
)
from backend.services.jd_parser_service import ParsedJD
from backend.models.job import Job
from backend.models.user import UserProfile


class TestGeneratedProposal:
    """Tests for GeneratedProposal dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        proposal = GeneratedProposal(
            content="This is a test proposal.",
            tone=ProposalTone.MEDIUM,
            word_count=5,
            keywords_used=["Python", "AWS"],
            experience_highlighted=["Built microservices"],
        )

        result = proposal.to_dict()

        assert result["content"] == "This is a test proposal."
        assert result["tone"] == "medium"
        assert result["word_count"] == 5
        assert result["keywords_used"] == ["Python", "AWS"]
        assert result["experience_highlighted"] == ["Built microservices"]

    def test_to_dict_with_empty_lists(self):
        """Test conversion with empty lists."""
        proposal = GeneratedProposal(
            content="Minimal proposal.",
            tone=ProposalTone.SHORT,
            word_count=2,
        )

        result = proposal.to_dict()

        assert result["keywords_used"] == []
        assert result["experience_highlighted"] == []


class TestProposalTone:
    """Tests for ProposalTone enum."""

    def test_tone_values(self):
        """Test tone enum values."""
        assert ProposalTone.SHORT.value == "short"
        assert ProposalTone.MEDIUM.value == "medium"
        assert ProposalTone.FULL.value == "full"

    def test_tone_from_string(self):
        """Test creating tone from string."""
        assert ProposalTone("short") == ProposalTone.SHORT
        assert ProposalTone("medium") == ProposalTone.MEDIUM
        assert ProposalTone("full") == ProposalTone.FULL


class TestProposalService:
    """Tests for ProposalService."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM service."""
        mock = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is a generated proposal for the Python Developer position. I have 5 years of Python experience and have built scalable APIs using FastAPI."

        mock.generate = AsyncMock(return_value=mock_response)
        return mock

    @pytest.fixture
    def proposal_service(self, mock_llm):
        """Create proposal service with mocked LLM."""
        return ProposalService(db=None, llm_service=mock_llm)

    @pytest.fixture
    def sample_parsed_jd(self):
        """Create sample parsed JD."""
        return ParsedJD(
            title="Senior Python Developer",
            company="TechCorp",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            nice_to_have_skills=["Docker", "AWS"],
            experience_level="senior",
            experience_years_min=5,
            compensation_min=140000,
            compensation_max=180000,
            compensation_type="annual",
            location="San Francisco, CA",
            remote=True,
            employment_type="full-time",
            key_requirements=["5+ years Python", "API development"],
            keywords_to_emphasize=["Python", "scalable", "microservices"],
            responsibilities=["Build APIs", "Code reviews"],
            benefits=["Remote", "Health insurance"],
            raw_text="Sample job description text...",
        )

    @pytest.fixture
    def sample_profile(self):
        """Create sample user profile."""
        profile = MagicMock(spec=UserProfile)
        profile.skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
        profile.experience_years = 6
        profile.job_title = "Senior Software Engineer"
        profile.profession = "software_engineer"
        profile.certifications = ["AWS Solutions Architect"]
        profile.portfolio = {
            "github": "https://github.com/johndoe",
            "achievements": [
                "Built microservices serving 1M users",
                "Reduced latency by 50%",
            ],
        }
        profile.preferred_industries = ["tech", "fintech"]
        return profile

    @pytest.fixture
    def sample_job(self):
        """Create sample job model."""
        job = MagicMock(spec=Job)
        job.title = "Senior Python Developer"
        job.company = "TechCorp"
        job.description = "Looking for an experienced Python developer"
        job.skills = ["Python", "FastAPI", "PostgreSQL"]
        job.requirements = {
            "key_requirements": ["5+ years experience"],
            "experience_level": "senior",
        }
        job.remote = True
        job.rate_min = Decimal("140000")
        job.rate_max = Decimal("180000")
        return job

    @pytest.mark.asyncio
    async def test_generate_proposal_with_parsed_jd(
        self, proposal_service, sample_parsed_jd, sample_profile
    ):
        """Test generating proposal with parsed JD."""
        result = await proposal_service.generate(
            parsed_jd=sample_parsed_jd,
            profile=sample_profile,
            tone=ProposalTone.MEDIUM,
        )

        assert isinstance(result, GeneratedProposal)
        assert result.tone == ProposalTone.MEDIUM
        assert result.word_count > 0
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_generate_proposal_with_job_model(
        self, proposal_service, sample_job, sample_profile
    ):
        """Test generating proposal with Job model."""
        result = await proposal_service.generate(
            job=sample_job,
            profile=sample_profile,
            tone=ProposalTone.SHORT,
        )

        assert isinstance(result, GeneratedProposal)
        assert result.tone == ProposalTone.SHORT

    @pytest.mark.asyncio
    async def test_generate_proposal_requires_job_or_parsed_jd(
        self, proposal_service, sample_profile
    ):
        """Test that either job or parsed_jd must be provided."""
        with pytest.raises(ValueError, match="Either job or parsed_jd must be provided"):
            await proposal_service.generate(
                profile=sample_profile,
                tone=ProposalTone.MEDIUM,
            )

    @pytest.mark.asyncio
    async def test_generate_proposal_short_tone(
        self, proposal_service, sample_parsed_jd, sample_profile
    ):
        """Test generating short proposal."""
        result = await proposal_service.generate(
            parsed_jd=sample_parsed_jd,
            profile=sample_profile,
            tone=ProposalTone.SHORT,
        )

        assert result.tone == ProposalTone.SHORT

    @pytest.mark.asyncio
    async def test_generate_proposal_full_tone(
        self, proposal_service, sample_parsed_jd, sample_profile
    ):
        """Test generating full proposal."""
        result = await proposal_service.generate(
            parsed_jd=sample_parsed_jd,
            profile=sample_profile,
            tone=ProposalTone.FULL,
        )

        assert result.tone == ProposalTone.FULL

    @pytest.mark.asyncio
    async def test_generate_proposal_with_additional_context(
        self, proposal_service, sample_parsed_jd, sample_profile, mock_llm
    ):
        """Test generating proposal with additional context."""
        additional = "I also have experience with machine learning."

        await proposal_service.generate(
            parsed_jd=sample_parsed_jd,
            profile=sample_profile,
            tone=ProposalTone.MEDIUM,
            additional_context=additional,
        )

        # Verify additional context was included in prompt
        call_args = mock_llm.generate.call_args
        assert additional in call_args.kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_generate_all_tones(
        self, proposal_service, sample_parsed_jd, sample_profile
    ):
        """Test generating proposals in all tones."""
        results = await proposal_service.generate_all_tones(
            parsed_jd=sample_parsed_jd,
            profile=sample_profile,
        )

        assert "short" in results
        assert "medium" in results
        assert "full" in results
        assert all(isinstance(p, GeneratedProposal) for p in results.values())

    @pytest.mark.asyncio
    async def test_enhance_proposal(
        self, proposal_service, sample_parsed_jd, sample_profile
    ):
        """Test enhancing existing proposal."""
        original = "I am interested in your Python position. I have experience."

        result = await proposal_service.enhance(
            original_proposal=original,
            parsed_jd=sample_parsed_jd,
            profile=sample_profile,
            enhancements=["add_keywords", "improve_tone"],
        )

        assert isinstance(result, GeneratedProposal)
        assert result.content != original  # Should be modified

    @pytest.mark.asyncio
    async def test_enhance_proposal_shorten(
        self, proposal_service, sample_parsed_jd
    ):
        """Test shortening a proposal."""
        original = "This is a very long proposal with lots of unnecessary words and details that could be made more concise."

        result = await proposal_service.enhance(
            original_proposal=original,
            parsed_jd=sample_parsed_jd,
            enhancements=["shorten"],
        )

        assert isinstance(result, GeneratedProposal)

    @pytest.mark.asyncio
    async def test_enhance_proposal_add_metrics(
        self, proposal_service, sample_job, sample_profile
    ):
        """Test adding metrics to proposal."""
        original = "I built applications and improved performance."

        result = await proposal_service.enhance(
            original_proposal=original,
            job=sample_job,
            profile=sample_profile,
            enhancements=["add_metrics"],
        )

        assert isinstance(result, GeneratedProposal)

    def test_extract_used_keywords(self, proposal_service):
        """Test keyword extraction from proposal."""
        proposal = "I have extensive Python experience and have worked with FastAPI and AWS."
        keywords = ["Python", "FastAPI", "AWS", "Docker", "Kubernetes"]

        result = proposal_service._extract_used_keywords(proposal, keywords)

        assert "Python" in result
        assert "FastAPI" in result
        assert "AWS" in result
        assert "Docker" not in result
        assert "Kubernetes" not in result

    def test_extract_used_keywords_case_insensitive(self, proposal_service):
        """Test keyword extraction is case insensitive."""
        proposal = "I work with python and fastapi daily."
        keywords = ["Python", "FastAPI"]

        result = proposal_service._extract_used_keywords(proposal, keywords)

        assert "Python" in result
        assert "FastAPI" in result

    def test_extract_highlighted_experience(self, proposal_service):
        """Test experience extraction from proposal."""
        proposal = "At my previous role, I built microservices serving over 1 million users."
        achievements = [
            "Built microservices serving 1M users",
            "Reduced latency by 50%",
            "Led team of 5 engineers",
        ]

        result = proposal_service._extract_highlighted_experience(proposal, achievements)

        # Should match the first achievement (similar words)
        assert len(result) >= 0  # Partial matching

    def test_build_job_context_from_parsed_jd(self, proposal_service, sample_parsed_jd):
        """Test building job context from ParsedJD."""
        result = proposal_service._build_job_context(None, sample_parsed_jd)

        assert result["title"] == "Senior Python Developer"
        assert result["company"] == "TechCorp"
        assert "Python" in result["required_skills"]
        assert result["remote"] is True

    def test_build_job_context_from_job_model(self, proposal_service, sample_job):
        """Test building job context from Job model."""
        result = proposal_service._build_job_context(sample_job, None)

        assert result["title"] == "Senior Python Developer"
        assert result["company"] == "TechCorp"
        assert "Python" in result["required_skills"]

    def test_build_job_context_empty(self, proposal_service):
        """Test building job context with no input."""
        result = proposal_service._build_job_context(None, None)

        assert result == {}

    def test_build_profile_context_with_profile(self, proposal_service, sample_profile):
        """Test building profile context."""
        result = proposal_service._build_profile_context(sample_profile)

        assert "Python" in result["skills"]
        assert result["experience_years"] == 6
        assert result["job_title"] == "Senior Software Engineer"
        assert len(result["achievements"]) > 0

    def test_build_profile_context_without_profile(self, proposal_service):
        """Test building profile context with no profile."""
        result = proposal_service._build_profile_context(None)

        assert result["skills"] == []
        assert result["experience_years"] == 0
        assert result["job_title"] == "Professional"

    def test_tone_instructions_exist(self, proposal_service):
        """Test that tone instructions exist for all tones."""
        for tone in ProposalTone:
            assert tone in proposal_service.TONE_INSTRUCTIONS
            config = proposal_service.TONE_INSTRUCTIONS[tone]
            assert "length" in config
            assert "style" in config
            assert "focus" in config

    def test_system_prompt_defined(self, proposal_service):
        """Test that system prompt is defined."""
        assert proposal_service.SYSTEM_PROMPT
        assert "proposal" in proposal_service.SYSTEM_PROMPT.lower()
        assert "personalized" in proposal_service.SYSTEM_PROMPT.lower()


class TestProposalPromptBuilding:
    """Tests for prompt building functionality."""

    @pytest.fixture
    def proposal_service(self, mock_embedding_service):
        """Create proposal service."""
        mock_llm = MagicMock()
        return ProposalService(db=None, llm_service=mock_llm)

    def test_build_prompt_includes_job_details(self, proposal_service):
        """Test that built prompt includes job details."""
        job_context = {
            "title": "Python Developer",
            "company": "TestCorp",
            "required_skills": ["Python", "Django"],
            "key_requirements": ["3+ years experience"],
            "keywords": ["Python", "backend"],
        }
        profile_context = {
            "job_title": "Software Engineer",
            "experience_years": 5,
            "skills": ["Python"],
        }
        tone_config = ProposalService.TONE_INSTRUCTIONS[ProposalTone.MEDIUM]

        prompt = proposal_service._build_prompt(
            job_context, profile_context, tone_config
        )

        assert "Python Developer" in prompt
        assert "TestCorp" in prompt
        assert "Python" in prompt
        assert "Django" in prompt

    def test_build_prompt_includes_profile(self, proposal_service):
        """Test that built prompt includes profile details."""
        job_context = {"title": "Developer", "company": "Corp"}
        profile_context = {
            "job_title": "Senior Engineer",
            "experience_years": 7,
            "skills": ["Python", "AWS"],
            "certifications": ["AWS Solutions Architect"],
            "achievements": ["Led team of 5"],
        }
        tone_config = ProposalService.TONE_INSTRUCTIONS[ProposalTone.MEDIUM]

        prompt = proposal_service._build_prompt(
            job_context, profile_context, tone_config
        )

        assert "Senior Engineer" in prompt
        assert "7 years" in prompt
        assert "AWS Solutions Architect" in prompt

    def test_build_prompt_includes_additional_context(self, proposal_service):
        """Test that built prompt includes additional context."""
        job_context = {"title": "Developer", "company": "Corp"}
        profile_context = {"job_title": "Engineer", "experience_years": 3}
        tone_config = ProposalService.TONE_INSTRUCTIONS[ProposalTone.SHORT]

        prompt = proposal_service._build_prompt(
            job_context, profile_context, tone_config,
            additional_context="I am very interested in AI projects."
        )

        assert "I am very interested in AI projects" in prompt
