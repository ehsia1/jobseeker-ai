"""Template service for resume and cover letter templates."""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.templates import (
    ResumeTemplate,
    RESUME_TEMPLATES,
    get_resume_template,
    get_resume_templates_for_industry,
    CoverLetterTemplate,
    COVER_LETTER_TEMPLATES,
    get_cover_letter_template,
    get_cover_letter_templates_for_industry,
)
from backend.config.industry_config import (
    Industry,
    IndustryConfig,
    INDUSTRY_CONFIGS,
    get_industry_config,
    get_industry_for_profession,
)
from backend.services.llm_service import get_llm_service, LLMService

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing and applying templates."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize template service.

        Args:
            llm_service: Optional LLM service for generating content
        """
        self.llm = llm_service or get_llm_service()

    # Resume Templates

    def get_all_resume_templates(self) -> List[ResumeTemplate]:
        """Get all available resume templates.

        Returns:
            List of all ResumeTemplate objects
        """
        return list(RESUME_TEMPLATES.values())

    def get_resume_template(self, template_id: str) -> Optional[ResumeTemplate]:
        """Get a specific resume template.

        Args:
            template_id: The template identifier

        Returns:
            ResumeTemplate if found, None otherwise
        """
        return get_resume_template(template_id)

    def get_resume_templates_by_industry(self, industry: str) -> List[ResumeTemplate]:
        """Get resume templates for a specific industry.

        Args:
            industry: Industry name (e.g., 'technology', 'healthcare')

        Returns:
            List of matching ResumeTemplate objects
        """
        return get_resume_templates_for_industry(industry)

    def get_resume_template_for_profession(
        self, profession: str
    ) -> Optional[ResumeTemplate]:
        """Get the best resume template for a profession.

        Args:
            profession: Profession name (e.g., 'software_engineer')

        Returns:
            Best matching ResumeTemplate or None
        """
        industry = get_industry_for_profession(profession)
        if not industry:
            # Return a default template
            return get_resume_template("tech_software_engineer")

        templates = get_resume_templates_for_industry(industry.value)
        return templates[0] if templates else None

    # Cover Letter Templates

    def get_all_cover_letter_templates(self) -> List[CoverLetterTemplate]:
        """Get all available cover letter templates.

        Returns:
            List of all CoverLetterTemplate objects
        """
        return list(COVER_LETTER_TEMPLATES.values())

    def get_cover_letter_template(
        self, template_id: str
    ) -> Optional[CoverLetterTemplate]:
        """Get a specific cover letter template.

        Args:
            template_id: The template identifier

        Returns:
            CoverLetterTemplate if found, None otherwise
        """
        return get_cover_letter_template(template_id)

    def get_cover_letter_templates_by_industry(
        self, industry: str
    ) -> List[CoverLetterTemplate]:
        """Get cover letter templates for a specific industry.

        Args:
            industry: Industry name

        Returns:
            List of matching CoverLetterTemplate objects
        """
        return get_cover_letter_templates_for_industry(industry)

    def get_cover_letter_template_for_profession(
        self, profession: str
    ) -> Optional[CoverLetterTemplate]:
        """Get the best cover letter template for a profession.

        Args:
            profession: Profession name

        Returns:
            Best matching CoverLetterTemplate or None
        """
        industry = get_industry_for_profession(profession)
        if not industry:
            return get_cover_letter_template("marketing_manager")

        templates = get_cover_letter_templates_for_industry(industry.value)
        return templates[0] if templates else None

    # Industry Config

    def get_all_industries(self) -> List[IndustryConfig]:
        """Get all industry configurations.

        Returns:
            List of all IndustryConfig objects
        """
        return list(INDUSTRY_CONFIGS.values())

    def get_industry(self, industry: str) -> Optional[IndustryConfig]:
        """Get configuration for a specific industry.

        Args:
            industry: Industry name

        Returns:
            IndustryConfig if found, None otherwise
        """
        return get_industry_config(industry)

    def get_industry_for_user_profession(
        self, profession: str
    ) -> Optional[IndustryConfig]:
        """Get the industry config for a user's profession.

        Args:
            profession: User's profession

        Returns:
            IndustryConfig for the profession's industry
        """
        industry = get_industry_for_profession(profession)
        if industry:
            return get_industry_config(industry.value)
        return None

    # Content Generation

    async def generate_resume_content(
        self,
        template_id: str,
        user_data: Dict[str, Any],
        job_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Generate resume content using a template and user data.

        Args:
            template_id: Resume template to use
            user_data: User's resume data (skills, experience, etc.)
            job_data: Optional job posting data for tailoring

        Returns:
            Dictionary with generated content for each section
        """
        template = self.get_resume_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        generated_sections = {}

        for section in template.sections:
            if section.name == "header":
                # Header is just contact info, no generation needed
                continue

            content = await self._generate_section_content(
                section_name=section.name,
                section_tips=section.tips,
                user_data=user_data,
                job_data=job_data,
                template_keywords=template.keywords_to_include,
            )
            generated_sections[section.name] = content

        return generated_sections

    async def generate_cover_letter_content(
        self,
        template_id: str,
        user_data: Dict[str, Any],
        job_data: Dict[str, Any],
        company_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Generate cover letter content using a template.

        Args:
            template_id: Cover letter template to use
            user_data: User's resume/profile data
            job_data: Job posting data
            company_data: Optional company research data

        Returns:
            Dictionary with generated content for each section
        """
        template = self.get_cover_letter_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        generated_sections = {}

        for section in template.sections:
            if section.name == "header":
                continue

            content = await self._generate_cover_letter_section(
                section=section,
                template=template,
                user_data=user_data,
                job_data=job_data,
                company_data=company_data,
            )
            generated_sections[section.name] = content

        return generated_sections

    async def generate_full_cover_letter(
        self,
        template_id: str,
        user_data: Dict[str, Any],
        job_data: Dict[str, Any],
        company_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a complete cover letter.

        Args:
            template_id: Cover letter template to use
            user_data: User's resume/profile data
            job_data: Job posting data
            company_data: Optional company research data

        Returns:
            Complete cover letter text
        """
        template = self.get_cover_letter_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        system_prompt = f"""You are an expert cover letter writer specializing in {template.industry} careers.
Write compelling, personalized cover letters that:
- Match the {template.tone.value} tone appropriate for this industry
- Use the {template.format.value} format style
- Include relevant keywords: {', '.join(template.keywords_to_include[:10])}
- Avoid generic phrases: {', '.join(template.phrases_to_avoid[:5])}
- Stay within {template.length_guidance}

Be specific, quantify achievements, and show genuine interest in the company."""

        user_info = self._format_user_data(user_data)
        job_info = self._format_job_data(job_data)
        company_info = self._format_company_data(company_data) if company_data else ""

        prompt = f"""Write a cover letter for this job application.

USER BACKGROUND:
{user_info}

JOB POSTING:
{job_info}

{f'COMPANY RESEARCH:{chr(10)}{company_info}' if company_info else ''}

TEMPLATE GUIDANCE:
- Opening hooks to consider: {template.opening_hooks[0]}
- Closing statements to consider: {template.closing_statements[0]}
- Personalization tips: {template.personalization_tips[0]}

Write the complete cover letter. Do not include placeholders - write actual content based on the provided information.
If specific details are missing, make reasonable inferences based on the context."""

        try:
            result = await self.llm.generate(prompt, system_prompt)
            return result.strip()
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            raise ValueError(f"Failed to generate cover letter: {e}")

    async def _generate_section_content(
        self,
        section_name: str,
        section_tips: List[str],
        user_data: Dict[str, Any],
        job_data: Optional[Dict[str, Any]],
        template_keywords: List[str],
    ) -> str:
        """Generate content for a resume section."""
        tips_text = "\n".join(f"- {tip}" for tip in section_tips[:5])

        prompt = f"""Generate content for the "{section_name}" section of a resume.

User Data: {user_data}
{f'Target Job: {job_data}' if job_data else ''}

Section Tips:
{tips_text}

Keywords to include if relevant: {', '.join(template_keywords[:10])}

Generate professional, concise content for this section. Use bullet points where appropriate.
Focus on achievements and quantifiable results."""

        try:
            result = await self.llm.generate(prompt)
            return result.strip()
        except Exception as e:
            logger.error(f"Section generation failed: {e}")
            return ""

    async def _generate_cover_letter_section(
        self,
        section: Any,
        template: CoverLetterTemplate,
        user_data: Dict[str, Any],
        job_data: Dict[str, Any],
        company_data: Optional[Dict[str, Any]],
    ) -> str:
        """Generate content for a cover letter section."""
        tips_text = "\n".join(f"- {tip}" for tip in section.tips[:5])
        word_range = f"{section.word_count_range[0]}-{section.word_count_range[1]} words"

        prompt = f"""Write the "{section.display_name}" section of a cover letter.

Section Description: {section.description}
Target Length: {word_range}

User Background: {user_data}
Job Posting: {job_data}
{f'Company Info: {company_data}' if company_data else ''}

Writing Tips:
{tips_text}

Example Structure: {section.example[:200] if section.example else 'N/A'}

Write this section in a {template.tone.value} tone. Be specific and personalized."""

        try:
            result = await self.llm.generate(prompt)
            return result.strip()
        except Exception as e:
            logger.error(f"Cover letter section generation failed: {e}")
            return ""

    def _format_user_data(self, user_data: Dict[str, Any]) -> str:
        """Format user data for prompts."""
        parts = []

        if user_data.get("name"):
            parts.append(f"Name: {user_data['name']}")
        if user_data.get("title"):
            parts.append(f"Current Title: {user_data['title']}")
        if user_data.get("years_experience"):
            parts.append(f"Years of Experience: {user_data['years_experience']}")
        if user_data.get("skills"):
            skills = user_data["skills"]
            if isinstance(skills, list):
                parts.append(f"Key Skills: {', '.join(skills[:15])}")
        if user_data.get("experience"):
            exp = user_data["experience"]
            if isinstance(exp, list) and exp:
                recent = exp[0]
                parts.append(
                    f"Recent Experience: {recent.get('title', '')} at {recent.get('company', '')}"
                )
                if recent.get("achievements"):
                    parts.append(
                        f"Key Achievement: {recent['achievements'][0]}"
                    )

        return "\n".join(parts) if parts else "No user data provided"

    def _format_job_data(self, job_data: Dict[str, Any]) -> str:
        """Format job data for prompts."""
        parts = []

        if job_data.get("title"):
            parts.append(f"Position: {job_data['title']}")
        if job_data.get("company"):
            parts.append(f"Company: {job_data['company']}")
        if job_data.get("location"):
            parts.append(f"Location: {job_data['location']}")
        if job_data.get("description"):
            desc = job_data["description"][:500]
            parts.append(f"Description: {desc}")
        if job_data.get("requirements"):
            reqs = job_data["requirements"]
            if isinstance(reqs, list):
                parts.append(f"Requirements: {', '.join(reqs[:10])}")

        return "\n".join(parts) if parts else "No job data provided"

    def _format_company_data(self, company_data: Dict[str, Any]) -> str:
        """Format company data for prompts."""
        parts = []

        if company_data.get("name"):
            parts.append(f"Company: {company_data['name']}")
        if company_data.get("industry"):
            parts.append(f"Industry: {company_data['industry']}")
        if company_data.get("size"):
            parts.append(f"Size: {company_data['size']}")
        if company_data.get("mission"):
            parts.append(f"Mission: {company_data['mission']}")
        if company_data.get("recent_news"):
            parts.append(f"Recent News: {company_data['recent_news']}")

        return "\n".join(parts) if parts else ""


# Convenience functions
def get_template_service() -> TemplateService:
    """Get a template service instance."""
    return TemplateService()


async def generate_cover_letter(
    template_id: str,
    user_data: Dict[str, Any],
    job_data: Dict[str, Any],
    company_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a cover letter using the template service."""
    service = TemplateService()
    return await service.generate_full_cover_letter(
        template_id, user_data, job_data, company_data
    )
