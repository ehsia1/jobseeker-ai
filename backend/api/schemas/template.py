"""Pydantic schemas for Template API endpoints."""

from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


# Resume Template Schemas

class ResumeSectionSchema(BaseModel):
    """Schema for a resume section."""

    name: str = Field(..., description="Section identifier")
    display_name: str = Field(..., description="Human-readable section name")
    description: str = Field(..., description="Section description and purpose")
    required: bool = Field(True, description="Whether section is required")
    order: int = Field(0, description="Display order")
    tips: List[str] = Field(default_factory=list, description="Writing tips")
    example: str = Field("", description="Example content")


class ResumeTemplateSchema(BaseModel):
    """Schema for a resume template."""

    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    industry: str = Field(..., description="Target industry")
    style: str = Field(..., description="Template style (modern, traditional, etc.)")
    sections: List[ResumeSectionSchema] = Field(..., description="Template sections")
    formatting_tips: List[str] = Field(
        default_factory=list, description="Formatting guidelines"
    )
    keywords_to_include: List[str] = Field(
        default_factory=list, description="Recommended keywords"
    )
    common_mistakes: List[str] = Field(
        default_factory=list, description="Common mistakes to avoid"
    )
    ats_optimization_tips: List[str] = Field(
        default_factory=list, description="ATS optimization tips"
    )


class ResumeTemplateListResponse(BaseModel):
    """Response for listing resume templates."""

    templates: List[ResumeTemplateSchema]
    count: int


class ResumeTemplateResponse(BaseModel):
    """Response for a single resume template."""

    template: ResumeTemplateSchema


# Cover Letter Template Schemas

class CoverLetterSectionSchema(BaseModel):
    """Schema for a cover letter section."""

    name: str = Field(..., description="Section identifier")
    display_name: str = Field(..., description="Human-readable section name")
    description: str = Field(..., description="Section description")
    word_count_min: int = Field(0, description="Minimum word count")
    word_count_max: int = Field(100, description="Maximum word count")
    tips: List[str] = Field(default_factory=list, description="Writing tips")
    example: str = Field("", description="Example content")
    required: bool = Field(True, description="Whether section is required")


class CoverLetterTemplateSchema(BaseModel):
    """Schema for a cover letter template."""

    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    industry: str = Field(..., description="Target industry")
    role_type: str = Field(..., description="Target role type")
    tone: str = Field(..., description="Writing tone")
    format: str = Field(..., description="Letter format style")
    sections: List[CoverLetterSectionSchema] = Field(
        ..., description="Template sections"
    )
    opening_hooks: List[str] = Field(
        default_factory=list, description="Opening line examples"
    )
    closing_statements: List[str] = Field(
        default_factory=list, description="Closing statement examples"
    )
    keywords_to_include: List[str] = Field(
        default_factory=list, description="Recommended keywords"
    )
    phrases_to_avoid: List[str] = Field(
        default_factory=list, description="Phrases to avoid"
    )
    formatting_tips: List[str] = Field(
        default_factory=list, description="Formatting guidelines"
    )
    length_guidance: str = Field("", description="Length guidance")
    personalization_tips: List[str] = Field(
        default_factory=list, description="Personalization tips"
    )


class CoverLetterTemplateListResponse(BaseModel):
    """Response for listing cover letter templates."""

    templates: List[CoverLetterTemplateSchema]
    count: int


class CoverLetterTemplateResponse(BaseModel):
    """Response for a single cover letter template."""

    template: CoverLetterTemplateSchema


# Industry Config Schemas

class SalaryRangeSchema(BaseModel):
    """Schema for salary range by level."""

    entry: Tuple[int, int] = Field(..., description="Entry-level salary range")
    mid: Tuple[int, int] = Field(..., description="Mid-level salary range")
    senior: Tuple[int, int] = Field(..., description="Senior-level salary range")


class IndustryConfigSchema(BaseModel):
    """Schema for industry configuration."""

    name: str = Field(..., description="Industry identifier")
    display_name: str = Field(..., description="Human-readable name")
    job_boards: List[str] = Field(
        default_factory=list, description="Recommended job boards"
    )
    core_skills: List[str] = Field(
        default_factory=list, description="Core skills for the industry"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Valuable certifications"
    )
    salary_range: Dict[str, List[int]] = Field(
        default_factory=dict, description="Salary ranges by level"
    )
    resume_sections: List[str] = Field(
        default_factory=list, description="Recommended resume sections"
    )
    cover_letter_tone: str = Field("", description="Recommended cover letter tone")
    interview_types: List[str] = Field(
        default_factory=list, description="Common interview types"
    )


class IndustryConfigListResponse(BaseModel):
    """Response for listing industries."""

    industries: List[IndustryConfigSchema]
    count: int


class IndustryConfigResponse(BaseModel):
    """Response for a single industry config."""

    industry: IndustryConfigSchema


# Content Generation Schemas

class GenerateCoverLetterRequest(BaseModel):
    """Request to generate a cover letter."""

    template_id: str = Field(..., description="Cover letter template to use")
    user_data: Dict[str, Any] = Field(
        ..., description="User's profile/resume data"
    )
    job_data: Dict[str, Any] = Field(..., description="Job posting data")
    company_data: Optional[Dict[str, Any]] = Field(
        None, description="Optional company research"
    )


class GenerateCoverLetterResponse(BaseModel):
    """Response with generated cover letter."""

    cover_letter: str = Field(..., description="Generated cover letter text")
    template_used: str = Field(..., description="Template ID used")
    word_count: int = Field(..., description="Word count of generated letter")


class GenerateResumeContentRequest(BaseModel):
    """Request to generate resume section content."""

    template_id: str = Field(..., description="Resume template to use")
    user_data: Dict[str, Any] = Field(..., description="User's resume data")
    job_data: Optional[Dict[str, Any]] = Field(
        None, description="Optional job posting to tailor for"
    )
    sections: Optional[List[str]] = Field(
        None, description="Specific sections to generate (all if not specified)"
    )


class GenerateResumeContentResponse(BaseModel):
    """Response with generated resume content."""

    sections: Dict[str, str] = Field(
        ..., description="Generated content by section name"
    )
    template_used: str = Field(..., description="Template ID used")


# Template Recommendation Schemas

class TemplateRecommendationRequest(BaseModel):
    """Request for template recommendations."""

    profession: Optional[str] = Field(None, description="User's profession")
    industry: Optional[str] = Field(None, description="Target industry")
    experience_level: Optional[str] = Field(
        None, description="Experience level (entry, mid, senior)"
    )


class TemplateRecommendationResponse(BaseModel):
    """Response with template recommendations."""

    resume_templates: List[ResumeTemplateSchema]
    cover_letter_templates: List[CoverLetterTemplateSchema]
    industry_config: Optional[IndustryConfigSchema]
