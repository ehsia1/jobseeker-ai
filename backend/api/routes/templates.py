"""Template routes for resume and cover letter templates."""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query
# Import directly to avoid circular imports through services __init__
from backend.services.template_service import TemplateService
from backend.api.schemas.template import (
    ResumeTemplateSchema,
    ResumeTemplateListResponse,
    ResumeTemplateResponse,
    ResumeSectionSchema,
    CoverLetterTemplateSchema,
    CoverLetterTemplateListResponse,
    CoverLetterTemplateResponse,
    CoverLetterSectionSchema,
    IndustryConfigSchema,
    IndustryConfigListResponse,
    IndustryConfigResponse,
    GenerateCoverLetterRequest,
    GenerateCoverLetterResponse,
    GenerateResumeContentRequest,
    GenerateResumeContentResponse,
    TemplateRecommendationRequest,
    TemplateRecommendationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _resume_template_to_schema(template) -> ResumeTemplateSchema:
    """Convert ResumeTemplate dataclass to schema."""
    return ResumeTemplateSchema(
        id=template.id,
        name=template.name,
        industry=template.industry,
        style=template.style.value if hasattr(template.style, "value") else str(template.style),
        sections=[
            ResumeSectionSchema(
                name=s.name,
                display_name=s.display_name,
                description=s.description,
                required=s.required,
                order=s.order,
                tips=s.tips,
                example=s.example,
            )
            for s in template.sections
        ],
        formatting_tips=template.formatting_tips,
        keywords_to_include=template.keywords_to_include,
        common_mistakes=template.common_mistakes,
        ats_optimization_tips=template.ats_optimization_tips,
    )


def _cover_letter_template_to_schema(template) -> CoverLetterTemplateSchema:
    """Convert CoverLetterTemplate dataclass to schema."""
    return CoverLetterTemplateSchema(
        id=template.id,
        name=template.name,
        industry=template.industry,
        role_type=template.role_type,
        tone=template.tone.value if hasattr(template.tone, "value") else str(template.tone),
        format=template.format.value if hasattr(template.format, "value") else str(template.format),
        sections=[
            CoverLetterSectionSchema(
                name=s.name,
                display_name=s.display_name,
                description=s.description,
                word_count_min=s.word_count_range[0],
                word_count_max=s.word_count_range[1],
                tips=s.tips,
                example=s.example,
                required=s.required,
            )
            for s in template.sections
        ],
        opening_hooks=template.opening_hooks,
        closing_statements=template.closing_statements,
        keywords_to_include=template.keywords_to_include,
        phrases_to_avoid=template.phrases_to_avoid,
        formatting_tips=template.formatting_tips,
        length_guidance=template.length_guidance,
        personalization_tips=template.personalization_tips,
    )


def _industry_config_to_schema(config) -> IndustryConfigSchema:
    """Convert IndustryConfig dataclass to schema."""
    salary_ranges = {}
    if config.salary_range:
        for level, range_tuple in config.salary_range.items():
            salary_ranges[level] = list(range_tuple)

    return IndustryConfigSchema(
        name=config.name,
        display_name=config.display_name,
        job_boards=config.job_boards,
        core_skills=config.core_skills,
        certifications=config.certifications,
        salary_range=salary_ranges,
        resume_sections=config.resume_sections,
        cover_letter_tone=config.cover_letter_tone,
        interview_types=config.interview_types,
    )


# Resume Template Endpoints

@router.get("/resume", response_model=ResumeTemplateListResponse)
async def list_resume_templates(
    industry: Optional[str] = Query(None, description="Filter by industry"),
):
    """List all available resume templates.

    Optionally filter by industry (technology, healthcare, finance, etc.).
    """
    service = TemplateService()

    if industry:
        templates = service.get_resume_templates_by_industry(industry)
    else:
        templates = service.get_all_resume_templates()

    schemas = [_resume_template_to_schema(t) for t in templates]

    return ResumeTemplateListResponse(templates=schemas, count=len(schemas))


@router.get("/resume/{template_id}", response_model=ResumeTemplateResponse)
async def get_resume_template(template_id: str):
    """Get a specific resume template by ID.

    Returns detailed template information including:
    - Section structure and guidelines
    - Formatting tips
    - Keywords to include
    - Common mistakes to avoid
    - ATS optimization tips
    """
    service = TemplateService()
    template = service.get_resume_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume template not found: {template_id}",
        )

    return ResumeTemplateResponse(template=_resume_template_to_schema(template))


# Cover Letter Template Endpoints

@router.get("/cover-letter", response_model=CoverLetterTemplateListResponse)
async def list_cover_letter_templates(
    industry: Optional[str] = Query(None, description="Filter by industry"),
):
    """List all available cover letter templates.

    Optionally filter by industry.
    """
    service = TemplateService()

    if industry:
        templates = service.get_cover_letter_templates_by_industry(industry)
    else:
        templates = service.get_all_cover_letter_templates()

    schemas = [_cover_letter_template_to_schema(t) for t in templates]

    return CoverLetterTemplateListResponse(templates=schemas, count=len(schemas))


@router.get("/cover-letter/{template_id}", response_model=CoverLetterTemplateResponse)
async def get_cover_letter_template(template_id: str):
    """Get a specific cover letter template by ID.

    Returns detailed template information including:
    - Section structure and word counts
    - Tone and format guidelines
    - Opening hooks and closing statements
    - Keywords and phrases to include/avoid
    - Personalization tips
    """
    service = TemplateService()
    template = service.get_cover_letter_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cover letter template not found: {template_id}",
        )

    return CoverLetterTemplateResponse(
        template=_cover_letter_template_to_schema(template)
    )


# Industry Endpoints

@router.get("/industries", response_model=IndustryConfigListResponse)
async def list_industries():
    """List all supported industries with their configurations.

    Returns industry-specific information including:
    - Recommended job boards
    - Core skills and certifications
    - Salary ranges by level
    - Interview types
    """
    service = TemplateService()
    industries = service.get_all_industries()

    schemas = [_industry_config_to_schema(i) for i in industries]

    return IndustryConfigListResponse(industries=schemas, count=len(schemas))


@router.get("/industries/{industry}", response_model=IndustryConfigResponse)
async def get_industry(industry: str):
    """Get configuration for a specific industry.

    Returns detailed industry information for career planning.
    """
    service = TemplateService()
    config = service.get_industry(industry)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Industry not found: {industry}",
        )

    return IndustryConfigResponse(industry=_industry_config_to_schema(config))


# Content Generation Endpoints

@router.post("/generate/cover-letter", response_model=GenerateCoverLetterResponse)
async def generate_cover_letter(request: GenerateCoverLetterRequest):
    """Generate a personalized cover letter.

    Uses AI to generate a complete cover letter based on:
    - Selected template style
    - User's profile and experience
    - Job posting details
    - Optional company research

    Returns a complete, ready-to-use cover letter.
    """
    service = TemplateService()

    try:
        cover_letter = await service.generate_full_cover_letter(
            template_id=request.template_id,
            user_data=request.user_data,
            job_data=request.job_data,
            company_data=request.company_data,
        )

        word_count = len(cover_letter.split())

        return GenerateCoverLetterResponse(
            cover_letter=cover_letter,
            template_used=request.template_id,
            word_count=word_count,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cover letter. Please try again.",
        )


@router.post("/generate/resume-content", response_model=GenerateResumeContentResponse)
async def generate_resume_content(request: GenerateResumeContentRequest):
    """Generate content for resume sections.

    Uses AI to generate professional content for each resume section
    based on the selected template and user data.

    Optionally tailor content to a specific job posting.
    """
    service = TemplateService()

    try:
        sections = await service.generate_resume_content(
            template_id=request.template_id,
            user_data=request.user_data,
            job_data=request.job_data,
        )

        # Filter sections if specific ones requested
        if request.sections:
            sections = {k: v for k, v in sections.items() if k in request.sections}

        return GenerateResumeContentResponse(
            sections=sections,
            template_used=request.template_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Resume content generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate resume content. Please try again.",
        )


# Template Recommendation Endpoint

@router.post("/recommend", response_model=TemplateRecommendationResponse)
async def recommend_templates(request: TemplateRecommendationRequest):
    """Get template recommendations based on user profile.

    Recommends the best resume and cover letter templates
    based on profession, industry, and experience level.
    """
    service = TemplateService()

    resume_templates = []
    cover_letter_templates = []
    industry_config = None

    # Get templates based on profession
    if request.profession:
        resume_template = service.get_resume_template_for_profession(request.profession)
        if resume_template:
            resume_templates.append(_resume_template_to_schema(resume_template))

        cl_template = service.get_cover_letter_template_for_profession(request.profession)
        if cl_template:
            cover_letter_templates.append(_cover_letter_template_to_schema(cl_template))

        config = service.get_industry_for_user_profession(request.profession)
        if config:
            industry_config = _industry_config_to_schema(config)

    # Get templates based on industry
    elif request.industry:
        resume_templates = [
            _resume_template_to_schema(t)
            for t in service.get_resume_templates_by_industry(request.industry)
        ]
        cover_letter_templates = [
            _cover_letter_template_to_schema(t)
            for t in service.get_cover_letter_templates_by_industry(request.industry)
        ]

        config = service.get_industry(request.industry)
        if config:
            industry_config = _industry_config_to_schema(config)

    # Default: return all templates
    else:
        resume_templates = [
            _resume_template_to_schema(t)
            for t in service.get_all_resume_templates()[:3]
        ]
        cover_letter_templates = [
            _cover_letter_template_to_schema(t)
            for t in service.get_all_cover_letter_templates()[:3]
        ]

    return TemplateRecommendationResponse(
        resume_templates=resume_templates,
        cover_letter_templates=cover_letter_templates,
        industry_config=industry_config,
    )


# Health Check

@router.get("/health")
async def templates_health():
    """Check if the template service is operational."""
    service = TemplateService()

    resume_count = len(service.get_all_resume_templates())
    cover_letter_count = len(service.get_all_cover_letter_templates())
    industry_count = len(service.get_all_industries())

    llm_available = service.llm.is_available() if service.llm else False

    return {
        "status": "healthy",
        "resume_templates": resume_count,
        "cover_letter_templates": cover_letter_count,
        "industries": industry_count,
        "llm_available": llm_available,
        "content_generation": "available" if llm_available else "unavailable",
    }
