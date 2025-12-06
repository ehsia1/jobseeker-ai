"""Job Description Parser Service - Extract structured data from JD text."""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.services.llm_service import LLMService, get_llm_service
from backend.services.scoring_service import ScoringService, ScoreBreakdown
from backend.models.user import UserProfile

logger = logging.getLogger(__name__)


@dataclass
class ParsedJD:
    """Parsed job description data."""

    title: Optional[str] = None
    company: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)
    nice_to_have_skills: List[str] = field(default_factory=list)
    experience_level: Optional[str] = None  # junior, mid, senior, lead
    experience_years_min: Optional[int] = None
    experience_years_max: Optional[int] = None
    compensation_min: Optional[float] = None
    compensation_max: Optional[float] = None
    compensation_type: Optional[str] = None  # hourly, annual, monthly
    location: Optional[str] = None
    remote: bool = False
    employment_type: Optional[str] = None  # full-time, part-time, contract
    key_requirements: List[str] = field(default_factory=list)
    keywords_to_emphasize: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "company": self.company,
            "required_skills": self.required_skills,
            "nice_to_have_skills": self.nice_to_have_skills,
            "experience_level": self.experience_level,
            "experience_years_min": self.experience_years_min,
            "experience_years_max": self.experience_years_max,
            "compensation_min": self.compensation_min,
            "compensation_max": self.compensation_max,
            "compensation_type": self.compensation_type,
            "location": self.location,
            "remote": self.remote,
            "employment_type": self.employment_type,
            "key_requirements": self.key_requirements,
            "keywords_to_emphasize": self.keywords_to_emphasize,
            "responsibilities": self.responsibilities,
            "benefits": self.benefits,
        }


@dataclass
class JDParseResult:
    """Complete result of JD parsing including optional scoring."""

    parsed: ParsedJD
    match_score: Optional[ScoreBreakdown] = None
    explanation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"parsed": self.parsed.to_dict()}
        if self.match_score:
            result["match_score"] = self.match_score.to_dict()
        if self.explanation:
            result["explanation"] = self.explanation
        return result


class JDParserService:
    """Service for parsing job descriptions into structured data."""

    PARSE_SYSTEM_PROMPT = """You are an expert job description analyzer. Your task is to extract structured information from job postings.

Extract the following information:
- Job title
- Company name (if mentioned)
- Required skills (technical skills, tools, languages)
- Nice-to-have skills (optional/preferred skills)
- Experience level (junior, mid, senior, lead, principal)
- Years of experience required (minimum and maximum if range given)
- Compensation (salary/rate range and type: hourly, annual, monthly)
- Location (city, state, country)
- Remote work (true/false)
- Employment type (full-time, part-time, contract, freelance)
- Key requirements (main qualifications needed)
- Keywords to emphasize (important terms a candidate should use when applying)
- Responsibilities (main job duties)
- Benefits (perks, compensation extras)

Be thorough but concise. For skills, extract specific technologies and tools (e.g., "Python", "React", "AWS", not generic terms like "programming").
For keywords_to_emphasize, include terms that would make a proposal stand out."""

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        llm_service: Optional[LLMService] = None,
    ):
        """Initialize JD Parser service.

        Args:
            db: Optional database session for profile lookup.
            llm_service: Optional LLM service instance.
        """
        self.db = db
        self.llm_service = llm_service or get_llm_service()
        self.scoring_service = ScoringService()

    async def parse(self, jd_text: str) -> ParsedJD:
        """Parse raw job description text into structured data.

        Args:
            jd_text: Raw job description text (pasted or scraped).

        Returns:
            ParsedJD with extracted information.
        """
        if not jd_text or not jd_text.strip():
            raise ValueError("Job description text cannot be empty")

        prompt = f"""Analyze this job description and extract structured information.

JOB DESCRIPTION:
{jd_text}

Return a JSON object with these exact keys:
{{
    "title": "Job title or null",
    "company": "Company name or null",
    "required_skills": ["skill1", "skill2"],
    "nice_to_have_skills": ["skill1", "skill2"],
    "experience_level": "junior|mid|senior|lead|principal or null",
    "experience_years_min": number or null,
    "experience_years_max": number or null,
    "compensation_min": number or null,
    "compensation_max": number or null,
    "compensation_type": "hourly|annual|monthly or null",
    "location": "Location or null",
    "remote": true or false,
    "employment_type": "full-time|part-time|contract|freelance or null",
    "key_requirements": ["requirement1", "requirement2"],
    "keywords_to_emphasize": ["keyword1", "keyword2"],
    "responsibilities": ["responsibility1", "responsibility2"],
    "benefits": ["benefit1", "benefit2"]
}}"""

        try:
            result = await self.llm_service.generate_structured(
                prompt=prompt,
                system_prompt=self.PARSE_SYSTEM_PROMPT,
            )

            return ParsedJD(
                title=result.get("title"),
                company=result.get("company"),
                required_skills=result.get("required_skills", []),
                nice_to_have_skills=result.get("nice_to_have_skills", []),
                experience_level=result.get("experience_level"),
                experience_years_min=result.get("experience_years_min"),
                experience_years_max=result.get("experience_years_max"),
                compensation_min=result.get("compensation_min"),
                compensation_max=result.get("compensation_max"),
                compensation_type=result.get("compensation_type"),
                location=result.get("location"),
                remote=result.get("remote", False),
                employment_type=result.get("employment_type"),
                key_requirements=result.get("key_requirements", []),
                keywords_to_emphasize=result.get("keywords_to_emphasize", []),
                responsibilities=result.get("responsibilities", []),
                benefits=result.get("benefits", []),
                raw_text=jd_text,
            )
        except Exception as e:
            logger.error(f"Failed to parse JD: {e}")
            raise

    async def parse_and_score(
        self,
        jd_text: str,
        user_id: Optional[UUID] = None,
        profile: Optional[UserProfile] = None,
    ) -> JDParseResult:
        """Parse JD and score against user profile.

        Args:
            jd_text: Raw job description text.
            user_id: Optional user ID to fetch profile.
            profile: Optional profile to score against.

        Returns:
            JDParseResult with parsed data and optional score.
        """
        # Parse the JD
        parsed = await self.parse(jd_text)

        # If no profile provided, try to fetch one
        if profile is None and user_id is not None and self.db is not None:
            profile = await self._get_user_profile(user_id)

        # Score if we have a profile
        match_score = None
        explanation = None

        if profile is not None:
            # Create a pseudo-job object for scoring
            pseudo_job = self._create_pseudo_job(parsed)
            match_score = self.scoring_service.score_job(pseudo_job, profile)
            explanation = self.scoring_service.generate_explanation(
                pseudo_job, profile, match_score
            )

        return JDParseResult(
            parsed=parsed,
            match_score=match_score,
            explanation=explanation,
        )

    async def extract_keywords(self, jd_text: str) -> List[str]:
        """Extract important keywords from job description.

        Args:
            jd_text: Raw job description text.

        Returns:
            List of keywords to emphasize in applications.
        """
        prompt = f"""Extract the most important keywords and phrases from this job description.
Focus on:
1. Technical skills and tools
2. Industry terms
3. Key qualifications
4. Action words used for responsibilities

Return a JSON array of 10-15 keywords, ordered by importance.

JOB DESCRIPTION:
{jd_text}

Return format: ["keyword1", "keyword2", ...]"""

        try:
            result = await self.llm_service.generate_structured(prompt=prompt)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            return []

    async def _get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Fetch user profile from database."""
        if self.db is None:
            return None

        try:
            result = await self.db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to fetch user profile: {e}")
            return None

    def _create_pseudo_job(self, parsed: ParsedJD):
        """Create a pseudo-job object for scoring.

        This creates an object that mimics the Job model interface
        so it can be used with the ScoringService.
        """

        class PseudoJob:
            """Pseudo job object for scoring parsed JDs."""

            def __init__(self, parsed_jd: ParsedJD):
                self.title = parsed_jd.title or "Unknown Position"
                self.company = parsed_jd.company
                self.description = parsed_jd.raw_text
                self.skills = parsed_jd.required_skills
                self.location = parsed_jd.location
                self.remote = parsed_jd.remote
                self.rate_min = parsed_jd.compensation_min
                self.rate_max = parsed_jd.compensation_max
                self.rate_type = parsed_jd.compensation_type or "annual"
                self.employment_type = parsed_jd.employment_type
                self.requirements = {
                    "key_requirements": parsed_jd.key_requirements,
                    "experience_level": parsed_jd.experience_level,
                    "experience_years_min": parsed_jd.experience_years_min,
                    "experience_years_max": parsed_jd.experience_years_max,
                }
                self.posted_at = None  # No posting date for pasted JDs
                self.embedding = None
                self.job_embedding = None

        return PseudoJob(parsed)
