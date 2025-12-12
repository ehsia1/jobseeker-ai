"""
Integration tests for the Templates API routes.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock

from backend.api.main import app


@pytest.fixture
def mock_llm_service():
    """Mock the LLM service for template service."""
    with patch("backend.services.template_service.get_llm_service") as mock:
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Generated content")
        mock_llm.is_available = MagicMock(return_value=True)
        mock.return_value = mock_llm
        yield mock_llm


class TestResumeTemplateEndpoints:
    """Tests for resume template endpoints."""

    @pytest.mark.asyncio
    async def test_list_resume_templates(self, mock_llm_service):
        """Test listing all resume templates."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/resume")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] > 0
        assert isinstance(data["templates"], list)

    @pytest.mark.asyncio
    async def test_list_resume_templates_by_industry(self, mock_llm_service):
        """Test listing resume templates filtered by industry."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/resume?industry=technology")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        # All templates should be for the requested industry
        for template in data["templates"]:
            assert template["industry"] == "technology"

    @pytest.mark.asyncio
    async def test_get_resume_template_by_id(self, mock_llm_service):
        """Test getting a specific resume template."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/resume/tech_software_engineer")

        assert response.status_code == 200
        data = response.json()
        assert "template" in data
        template = data["template"]
        assert template["id"] == "tech_software_engineer"
        assert "sections" in template
        assert "formatting_tips" in template

    @pytest.mark.asyncio
    async def test_get_resume_template_not_found(self, mock_llm_service):
        """Test getting a non-existent resume template."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/resume/nonexistent_template")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCoverLetterTemplateEndpoints:
    """Tests for cover letter template endpoints."""

    @pytest.mark.asyncio
    async def test_list_cover_letter_templates(self, mock_llm_service):
        """Test listing all cover letter templates."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/cover-letter")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] > 0

    @pytest.mark.asyncio
    async def test_list_cover_letter_templates_by_industry(self, mock_llm_service):
        """Test listing cover letter templates filtered by industry."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/cover-letter?industry=technology")

        assert response.status_code == 200
        data = response.json()
        for template in data["templates"]:
            assert template["industry"] == "technology"

    @pytest.mark.asyncio
    async def test_get_cover_letter_template_by_id(self, mock_llm_service):
        """Test getting a specific cover letter template."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/cover-letter/tech_software_engineer")

        assert response.status_code == 200
        data = response.json()
        assert "template" in data
        template = data["template"]
        assert template["id"] == "tech_software_engineer"
        assert "sections" in template
        assert "opening_hooks" in template

    @pytest.mark.asyncio
    async def test_get_cover_letter_template_not_found(self, mock_llm_service):
        """Test getting a non-existent cover letter template."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/cover-letter/nonexistent")

        assert response.status_code == 404


class TestIndustryEndpoints:
    """Tests for industry configuration endpoints."""

    @pytest.mark.asyncio
    async def test_list_industries(self, mock_llm_service):
        """Test listing all industries."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/industries")

        assert response.status_code == 200
        data = response.json()
        assert "industries" in data
        assert "count" in data
        assert data["count"] > 0

        # Check industry structure
        for industry in data["industries"]:
            assert "name" in industry
            assert "display_name" in industry
            assert "job_boards" in industry

    @pytest.mark.asyncio
    async def test_get_specific_industry(self, mock_llm_service):
        """Test getting a specific industry configuration."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/industries/technology")

        assert response.status_code == 200
        data = response.json()
        assert "industry" in data
        industry = data["industry"]
        assert industry["name"] == "technology"
        assert "core_skills" in industry
        assert "job_boards" in industry

    @pytest.mark.asyncio
    async def test_get_industry_fallback_to_general(self, mock_llm_service):
        """Test getting a non-existent industry falls back to general."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/industries/nonexistent")

        # The service falls back to 'general' for unknown industries
        assert response.status_code == 200
        data = response.json()
        assert data["industry"]["name"] == "general"


class TestContentGenerationEndpoints:
    """Tests for content generation endpoints."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter(self, mock_llm_service):
        """Test generating a cover letter."""
        request_data = {
            "template_id": "tech_software_engineer",
            "user_data": {
                "name": "John Doe",
                "title": "Software Engineer",
                "skills": ["Python", "JavaScript"],
            },
            "job_data": {
                "title": "Senior Software Engineer",
                "company": "TechCorp",
                "description": "Looking for experienced engineers...",
            },
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/templates/generate/cover-letter",
                json=request_data,
            )

        assert response.status_code == 200
        data = response.json()
        assert "cover_letter" in data
        assert "template_used" in data
        assert "word_count" in data
        assert data["template_used"] == "tech_software_engineer"

    @pytest.mark.asyncio
    async def test_generate_cover_letter_invalid_template(self, mock_llm_service):
        """Test generating cover letter with invalid template."""
        request_data = {
            "template_id": "nonexistent",
            "user_data": {"name": "John"},
            "job_data": {"title": "Engineer"},
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/templates/generate/cover-letter",
                json=request_data,
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_resume_content(self, mock_llm_service):
        """Test generating resume content."""
        request_data = {
            "template_id": "tech_software_engineer",
            "user_data": {
                "name": "Jane Doe",
                "title": "Data Scientist",
                "skills": ["Python", "ML"],
            },
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/templates/generate/resume-content",
                json=request_data,
            )

        assert response.status_code == 200
        data = response.json()
        assert "sections" in data
        assert "template_used" in data

    @pytest.mark.asyncio
    async def test_generate_resume_content_with_job_data(self, mock_llm_service):
        """Test generating resume content tailored to job."""
        request_data = {
            "template_id": "tech_software_engineer",
            "user_data": {"name": "Jane Doe"},
            "job_data": {"title": "ML Engineer", "company": "AI Corp"},
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/templates/generate/resume-content",
                json=request_data,
            )

        assert response.status_code == 200


class TestTemplateRecommendationEndpoint:
    """Tests for template recommendation endpoint."""

    @pytest.mark.asyncio
    async def test_recommend_by_profession(self, mock_llm_service):
        """Test recommending templates by profession."""
        request_data = {"profession": "software_engineer"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/templates/recommend", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "resume_templates" in data
        assert "cover_letter_templates" in data
        assert "industry_config" in data

    @pytest.mark.asyncio
    async def test_recommend_by_industry(self, mock_llm_service):
        """Test recommending templates by industry."""
        request_data = {"industry": "technology"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/templates/recommend", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "resume_templates" in data
        assert "cover_letter_templates" in data

    @pytest.mark.asyncio
    async def test_recommend_default(self, mock_llm_service):
        """Test recommending templates with no filters."""
        request_data = {}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/templates/recommend", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "resume_templates" in data
        assert "cover_letter_templates" in data


class TestTemplatesHealthEndpoint:
    """Tests for templates health check endpoint."""

    @pytest.mark.asyncio
    async def test_templates_health(self, mock_llm_service):
        """Test templates health check endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/templates/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "resume_templates" in data
        assert "cover_letter_templates" in data
        assert "industries" in data
        assert data["resume_templates"] > 0
        assert data["cover_letter_templates"] > 0
