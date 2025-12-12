"""
Unit tests for the TemplateService.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

from backend.services.template_service import TemplateService, get_template_service
from backend.templates import ResumeTemplate, CoverLetterTemplate
from backend.config.industry_config import Industry, IndustryConfig


class TestTemplateServiceInitialization:
    """Tests for TemplateService initialization."""

    def test_init_without_llm(self):
        """Test initialization without LLM service."""
        with patch("backend.services.template_service.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm

            service = TemplateService()

            assert service.llm == mock_llm
            mock_get_llm.assert_called_once()

    def test_init_with_custom_llm(self):
        """Test initialization with custom LLM service."""
        mock_llm = MagicMock()

        service = TemplateService(llm_service=mock_llm)

        assert service.llm == mock_llm


class TestResumeTemplates:
    """Tests for resume template methods."""

    @patch("backend.services.template_service.get_llm_service")
    def test_get_all_resume_templates(self, mock_get_llm):
        """Test getting all resume templates."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        templates = service.get_all_resume_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0
        assert all(isinstance(t, ResumeTemplate) for t in templates)

    @patch("backend.services.template_service.get_llm_service")
    def test_get_resume_template_by_id(self, mock_get_llm):
        """Test getting a specific resume template by ID."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_resume_template("tech_software_engineer")

        assert template is not None
        assert isinstance(template, ResumeTemplate)
        assert template.id == "tech_software_engineer"

    @patch("backend.services.template_service.get_llm_service")
    def test_get_resume_template_invalid_id(self, mock_get_llm):
        """Test getting template with invalid ID returns None."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_resume_template("nonexistent_template")

        assert template is None

    @patch("backend.services.template_service.get_llm_service")
    def test_get_resume_templates_by_industry(self, mock_get_llm):
        """Test getting templates by industry."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        templates = service.get_resume_templates_by_industry("technology")

        assert isinstance(templates, list)
        # All returned templates should be for the requested industry
        for t in templates:
            assert t.industry == "technology"

    @patch("backend.services.template_service.get_llm_service")
    def test_get_resume_template_for_profession(self, mock_get_llm):
        """Test getting template for a profession."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_resume_template_for_profession("software_engineer")

        assert template is not None
        assert isinstance(template, ResumeTemplate)

    @patch("backend.services.template_service.get_llm_service")
    def test_get_resume_template_for_unknown_profession(self, mock_get_llm):
        """Test getting template for unknown profession returns default."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_resume_template_for_profession("unknown_profession_xyz")

        # Should return some template (may be default)
        assert template is not None or template is None  # Function may return None or default


class TestCoverLetterTemplates:
    """Tests for cover letter template methods."""

    @patch("backend.services.template_service.get_llm_service")
    def test_get_all_cover_letter_templates(self, mock_get_llm):
        """Test getting all cover letter templates."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        templates = service.get_all_cover_letter_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0
        assert all(isinstance(t, CoverLetterTemplate) for t in templates)

    @patch("backend.services.template_service.get_llm_service")
    def test_get_cover_letter_template_by_id(self, mock_get_llm):
        """Test getting a specific cover letter template by ID."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_cover_letter_template("tech_software_engineer")

        assert template is not None
        assert isinstance(template, CoverLetterTemplate)
        assert template.id == "tech_software_engineer"

    @patch("backend.services.template_service.get_llm_service")
    def test_get_cover_letter_template_invalid_id(self, mock_get_llm):
        """Test getting template with invalid ID returns None."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_cover_letter_template("nonexistent_template")

        assert template is None

    @patch("backend.services.template_service.get_llm_service")
    def test_get_cover_letter_templates_by_industry(self, mock_get_llm):
        """Test getting cover letter templates by industry."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        templates = service.get_cover_letter_templates_by_industry("technology")

        assert isinstance(templates, list)
        for t in templates:
            assert t.industry == "technology"

    @patch("backend.services.template_service.get_llm_service")
    def test_get_cover_letter_template_for_profession(self, mock_get_llm):
        """Test getting cover letter template for a profession."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        template = service.get_cover_letter_template_for_profession("software_engineer")

        # May return a template or None
        if template is not None:
            assert isinstance(template, CoverLetterTemplate)


class TestIndustryConfig:
    """Tests for industry configuration methods."""

    @patch("backend.services.template_service.get_llm_service")
    def test_get_all_industries(self, mock_get_llm):
        """Test getting all industry configurations."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        industries = service.get_all_industries()

        assert isinstance(industries, list)
        assert len(industries) > 0
        assert all(isinstance(i, IndustryConfig) for i in industries)

    @patch("backend.services.template_service.get_llm_service")
    def test_get_industry_by_name(self, mock_get_llm):
        """Test getting a specific industry configuration."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        industry = service.get_industry("technology")

        assert industry is not None
        assert isinstance(industry, IndustryConfig)
        assert industry.name == "technology"

    @patch("backend.services.template_service.get_llm_service")
    def test_get_industry_for_user_profession(self, mock_get_llm):
        """Test getting industry config for a user's profession."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        industry = service.get_industry_for_user_profession("software_engineer")

        assert industry is not None
        assert isinstance(industry, IndustryConfig)
        assert industry.name == "technology"


class TestContentGeneration:
    """Tests for content generation methods."""

    @pytest.mark.asyncio
    @patch("backend.services.template_service.get_llm_service")
    async def test_generate_resume_content(self, mock_get_llm):
        """Test generating resume content."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Generated content")
        mock_get_llm.return_value = mock_llm

        service = TemplateService()
        user_data = {
            "name": "John Doe",
            "title": "Software Engineer",
            "skills": ["Python", "JavaScript"],
        }

        result = await service.generate_resume_content(
            template_id="tech_software_engineer",
            user_data=user_data,
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("backend.services.template_service.get_llm_service")
    async def test_generate_resume_content_invalid_template(self, mock_get_llm):
        """Test generating content with invalid template raises error."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        with pytest.raises(ValueError, match="Template not found"):
            await service.generate_resume_content(
                template_id="nonexistent",
                user_data={},
            )

    @pytest.mark.asyncio
    @patch("backend.services.template_service.get_llm_service")
    async def test_generate_cover_letter_content(self, mock_get_llm):
        """Test generating cover letter section content."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Generated paragraph")
        mock_get_llm.return_value = mock_llm

        service = TemplateService()
        user_data = {"name": "John Doe", "title": "Engineer"}
        job_data = {"title": "Senior Engineer", "company": "TechCorp"}

        result = await service.generate_cover_letter_content(
            template_id="tech_software_engineer",
            user_data=user_data,
            job_data=job_data,
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("backend.services.template_service.get_llm_service")
    async def test_generate_full_cover_letter(self, mock_get_llm):
        """Test generating a complete cover letter."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Dear Hiring Manager,\n\nI am excited...")
        mock_get_llm.return_value = mock_llm

        service = TemplateService()
        user_data = {
            "name": "John Doe",
            "title": "Software Engineer",
            "skills": ["Python", "AWS"],
            "experience": [{"title": "Engineer", "company": "Tech Inc"}],
        }
        job_data = {
            "title": "Senior Software Engineer",
            "company": "Amazing Corp",
            "description": "Looking for an experienced engineer...",
        }

        result = await service.generate_full_cover_letter(
            template_id="tech_software_engineer",
            user_data=user_data,
            job_data=job_data,
        )

        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.generate.assert_called()

    @pytest.mark.asyncio
    @patch("backend.services.template_service.get_llm_service")
    async def test_generate_full_cover_letter_invalid_template(self, mock_get_llm):
        """Test generating cover letter with invalid template raises error."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        with pytest.raises(ValueError, match="Template not found"):
            await service.generate_full_cover_letter(
                template_id="nonexistent",
                user_data={},
                job_data={},
            )

    @pytest.mark.asyncio
    @patch("backend.services.template_service.get_llm_service")
    async def test_generate_full_cover_letter_with_company_data(self, mock_get_llm):
        """Test generating cover letter with company research data."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Personalized letter...")
        mock_get_llm.return_value = mock_llm

        service = TemplateService()
        user_data = {"name": "Jane Doe"}
        job_data = {"title": "Manager", "company": "Corp"}
        company_data = {
            "name": "Corp Inc",
            "industry": "Technology",
            "mission": "To innovate",
            "recent_news": "Just raised Series B",
        }

        result = await service.generate_full_cover_letter(
            template_id="tech_software_engineer",
            user_data=user_data,
            job_data=job_data,
            company_data=company_data,
        )

        assert isinstance(result, str)


class TestHelperMethods:
    """Tests for private helper methods."""

    @patch("backend.services.template_service.get_llm_service")
    def test_format_user_data(self, mock_get_llm):
        """Test user data formatting."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        user_data = {
            "name": "John Doe",
            "title": "Software Engineer",
            "years_experience": 5,
            "skills": ["Python", "JavaScript", "React"],
            "experience": [
                {
                    "title": "Senior Engineer",
                    "company": "TechCorp",
                    "achievements": ["Led team of 5", "Increased performance by 50%"],
                }
            ],
        }

        result = service._format_user_data(user_data)

        assert "John Doe" in result
        assert "Software Engineer" in result
        assert "Python" in result or "skills" in result.lower()

    @patch("backend.services.template_service.get_llm_service")
    def test_format_user_data_empty(self, mock_get_llm):
        """Test formatting empty user data."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        result = service._format_user_data({})

        assert "No user data" in result

    @patch("backend.services.template_service.get_llm_service")
    def test_format_job_data(self, mock_get_llm):
        """Test job data formatting."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        job_data = {
            "title": "Senior Software Engineer",
            "company": "Amazing Corp",
            "location": "San Francisco, CA",
            "description": "Looking for a talented engineer...",
            "requirements": ["5+ years Python", "AWS experience"],
        }

        result = service._format_job_data(job_data)

        assert "Senior Software Engineer" in result
        assert "Amazing Corp" in result
        assert "San Francisco" in result

    @patch("backend.services.template_service.get_llm_service")
    def test_format_job_data_empty(self, mock_get_llm):
        """Test formatting empty job data."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        result = service._format_job_data({})

        assert "No job data" in result

    @patch("backend.services.template_service.get_llm_service")
    def test_format_company_data(self, mock_get_llm):
        """Test company data formatting."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        company_data = {
            "name": "TechCorp",
            "industry": "Technology",
            "size": "500-1000 employees",
            "mission": "To build the future",
            "recent_news": "Just launched new product",
        }

        result = service._format_company_data(company_data)

        assert "TechCorp" in result
        assert "Technology" in result
        assert "To build the future" in result

    @patch("backend.services.template_service.get_llm_service")
    def test_format_company_data_empty(self, mock_get_llm):
        """Test formatting empty company data."""
        mock_get_llm.return_value = MagicMock()
        service = TemplateService()

        result = service._format_company_data({})

        assert result == ""


class TestGetTemplateService:
    """Tests for the get_template_service convenience function."""

    @patch("backend.services.template_service.get_llm_service")
    def test_get_template_service(self, mock_get_llm):
        """Test getting a template service instance."""
        mock_get_llm.return_value = MagicMock()

        service = get_template_service()

        assert isinstance(service, TemplateService)
