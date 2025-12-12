"""Template modules for resumes and cover letters."""

from backend.templates.resume_templates import (
    ResumeTemplate,
    RESUME_TEMPLATES,
    get_resume_template,
    get_resume_templates_for_industry,
)
from backend.templates.cover_letter_templates import (
    CoverLetterTemplate,
    COVER_LETTER_TEMPLATES,
    get_cover_letter_template,
    get_cover_letter_templates_for_industry,
)

__all__ = [
    "ResumeTemplate",
    "RESUME_TEMPLATES",
    "get_resume_template",
    "get_resume_templates_for_industry",
    "CoverLetterTemplate",
    "COVER_LETTER_TEMPLATES",
    "get_cover_letter_template",
    "get_cover_letter_templates_for_industry",
]
