"""Proposal Generator Service - Generate tailored proposals in multiple tones."""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.services.llm_service import LLMService, get_llm_service
from backend.services.jd_parser_service import ParsedJD
from backend.models.user import UserProfile
from backend.models.job import Job

logger = logging.getLogger(__name__)


class ProposalTone(str, Enum):
    """Proposal tone options."""

    SHORT = "short"
    MEDIUM = "medium"
    FULL = "full"


@dataclass
class GeneratedProposal:
    """Generated proposal with metadata."""

    content: str
    tone: ProposalTone
    word_count: int
    keywords_used: List[str] = field(default_factory=list)
    experience_highlighted: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "tone": self.tone.value,
            "word_count": self.word_count,
            "keywords_used": self.keywords_used,
            "experience_highlighted": self.experience_highlighted,
        }


class ProposalService:
    """Service for generating tailored job proposals."""

    TONE_INSTRUCTIONS = {
        ProposalTone.SHORT: {
            "length": "2-3 sentences (50-75 words)",
            "style": "Direct and punchy. Lead with your strongest qualification. End with a call to action.",
            "focus": "One key achievement that directly relates to their needs.",
        },
        ProposalTone.MEDIUM: {
            "length": "150-200 words",
            "style": "Professional yet personable. Show understanding of their problem, present your solution.",
            "focus": "2-3 relevant achievements with brief context. Include a specific example.",
        },
        ProposalTone.FULL: {
            "length": "300-400 words",
            "style": "Comprehensive and consultative. Demonstrate deep understanding of their business.",
            "focus": "Multiple relevant projects with outcomes. Include methodology, timeline hints, and next steps.",
        },
    }

    SYSTEM_PROMPT = """You are an expert proposal writer for freelancers and job seekers.
Your proposals are:
- Personalized (never generic templates)
- Results-focused (lead with outcomes, not responsibilities)
- Client-centric (focus on THEIR needs, not your background)
- Keyword-optimized (naturally incorporate relevant terms)
- Action-oriented (clear next steps)

Avoid:
- Generic openings like "I am writing to express my interest..."
- Listing skills without context
- Overused phrases like "passionate" or "dedicated professional"
- Vague claims without evidence
- Excessive flattery

Format rules:
- No headers or bullet points (unless explicitly asked)
- Write in first person
- Sound human, not AI-generated
- Match the client's communication style when possible"""

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        llm_service: Optional[LLMService] = None,
    ):
        """Initialize Proposal service.

        Args:
            db: Optional database session for profile lookup.
            llm_service: Optional LLM service instance.
        """
        self.db = db
        self.llm_service = llm_service or get_llm_service()

    async def generate(
        self,
        job: Optional[Job] = None,
        parsed_jd: Optional[ParsedJD] = None,
        profile: Optional[UserProfile] = None,
        user_id: Optional[UUID] = None,
        tone: ProposalTone = ProposalTone.MEDIUM,
        additional_context: Optional[str] = None,
    ) -> GeneratedProposal:
        """Generate a tailored proposal.

        Args:
            job: Job model from database (optional).
            parsed_jd: Parsed JD from text (optional). One of job or parsed_jd required.
            profile: User profile (optional, will be fetched if user_id provided).
            user_id: User ID for profile lookup (optional).
            tone: Proposal tone (short/medium/full).
            additional_context: Extra context from user (e.g., specific points to mention).

        Returns:
            GeneratedProposal with content and metadata.
        """
        # Validate input
        if not job and not parsed_jd:
            raise ValueError("Either job or parsed_jd must be provided")

        # Get profile if needed
        if profile is None and user_id is not None and self.db is not None:
            profile = await self._get_user_profile(user_id)

        # Build job context
        job_context = self._build_job_context(job, parsed_jd)

        # Build profile context
        profile_context = self._build_profile_context(profile)

        # Get tone instructions
        tone_config = self.TONE_INSTRUCTIONS[tone]

        # Build the prompt
        prompt = self._build_prompt(
            job_context=job_context,
            profile_context=profile_context,
            tone_config=tone_config,
            additional_context=additional_context,
        )

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
            )

            proposal_text = response.content.strip()

            # Extract keywords that were used
            keywords_used = self._extract_used_keywords(
                proposal_text, job_context.get("keywords", [])
            )

            # Extract highlighted experience
            experience_highlighted = self._extract_highlighted_experience(
                proposal_text, profile_context.get("achievements", [])
            )

            return GeneratedProposal(
                content=proposal_text,
                tone=tone,
                word_count=len(proposal_text.split()),
                keywords_used=keywords_used,
                experience_highlighted=experience_highlighted,
            )

        except Exception as e:
            logger.error(f"Failed to generate proposal: {e}")
            raise

    async def generate_all_tones(
        self,
        job: Optional[Job] = None,
        parsed_jd: Optional[ParsedJD] = None,
        profile: Optional[UserProfile] = None,
        user_id: Optional[UUID] = None,
        additional_context: Optional[str] = None,
    ) -> Dict[str, GeneratedProposal]:
        """Generate proposals in all three tones.

        Returns:
            Dictionary with tone as key and GeneratedProposal as value.
        """
        results = {}

        for tone in ProposalTone:
            proposal = await self.generate(
                job=job,
                parsed_jd=parsed_jd,
                profile=profile,
                user_id=user_id,
                tone=tone,
                additional_context=additional_context,
            )
            results[tone.value] = proposal

        return results

    async def enhance(
        self,
        original_proposal: str,
        job: Optional[Job] = None,
        parsed_jd: Optional[ParsedJD] = None,
        profile: Optional[UserProfile] = None,
        enhancements: Optional[List[str]] = None,
    ) -> GeneratedProposal:
        """Enhance an existing proposal.

        Args:
            original_proposal: The user's draft proposal.
            job: Job context (optional).
            parsed_jd: Parsed JD (optional).
            profile: User profile for personalization (optional).
            enhancements: List of enhancement types:
                - "add_keywords": Naturally incorporate relevant keywords
                - "improve_tone": Make more professional/engaging
                - "add_metrics": Add quantified achievements
                - "shorten": Make more concise
                - "expand": Add more detail and examples

        Returns:
            Enhanced proposal.
        """
        enhancements = enhancements or ["improve_tone", "add_keywords"]

        # Build context
        job_context = self._build_job_context(job, parsed_jd)
        profile_context = self._build_profile_context(profile)

        enhancement_instructions = []
        if "add_keywords" in enhancements:
            keywords = job_context.get("keywords", [])
            if keywords:
                enhancement_instructions.append(
                    f"Naturally incorporate these keywords: {', '.join(keywords[:5])}"
                )

        if "improve_tone" in enhancements:
            enhancement_instructions.append(
                "Improve the tone to be more professional yet personable"
            )

        if "add_metrics" in enhancements:
            enhancement_instructions.append(
                "Add specific metrics or quantified achievements where possible"
            )

        if "shorten" in enhancements:
            enhancement_instructions.append(
                "Make the proposal more concise while keeping key points"
            )

        if "expand" in enhancements:
            enhancement_instructions.append(
                "Expand with more detail and specific examples"
            )

        prompt = f"""Enhance this job proposal while maintaining the author's voice.

ORIGINAL PROPOSAL:
{original_proposal}

JOB CONTEXT:
{self._format_job_context(job_context)}

ENHANCEMENT INSTRUCTIONS:
{chr(10).join(f"- {inst}" for inst in enhancement_instructions)}

Return ONLY the enhanced proposal text. No explanations or headers."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
            )

            enhanced_text = response.content.strip()

            return GeneratedProposal(
                content=enhanced_text,
                tone=ProposalTone.MEDIUM,  # Enhanced proposals default to medium
                word_count=len(enhanced_text.split()),
                keywords_used=self._extract_used_keywords(
                    enhanced_text, job_context.get("keywords", [])
                ),
                experience_highlighted=[],
            )

        except Exception as e:
            logger.error(f"Failed to enhance proposal: {e}")
            raise

    def _build_job_context(
        self, job: Optional[Job], parsed_jd: Optional[ParsedJD]
    ) -> Dict[str, Any]:
        """Build job context dictionary from Job model or ParsedJD."""
        if parsed_jd:
            return {
                "title": parsed_jd.title or "Unknown Position",
                "company": parsed_jd.company or "the company",
                "required_skills": parsed_jd.required_skills,
                "nice_to_have_skills": parsed_jd.nice_to_have_skills,
                "key_requirements": parsed_jd.key_requirements,
                "keywords": parsed_jd.keywords_to_emphasize,
                "responsibilities": parsed_jd.responsibilities,
                "experience_level": parsed_jd.experience_level,
                "remote": parsed_jd.remote,
                "description": parsed_jd.raw_text[:1000],  # Truncate for prompt
            }
        elif job:
            # requirements is a JSONB list, not a dict
            requirements_list = job.requirements or []
            return {
                "title": job.title,
                "company": job.company or "the company",
                "required_skills": job.skills or [],
                "nice_to_have_skills": [],
                "key_requirements": requirements_list if isinstance(requirements_list, list) else [],
                "keywords": [],  # Would need to extract
                "responsibilities": [],
                "experience_level": None,  # Not stored in current schema
                "remote": job.remote,
                "description": job.description[:1000] if job.description else "",
            }
        return {}

    def _build_profile_context(
        self, profile: Optional[UserProfile]
    ) -> Dict[str, Any]:
        """Build profile context dictionary."""
        if not profile:
            return {
                "skills": [],
                "experience_years": 0,
                "job_title": "Professional",
                "achievements": [],
                "portfolio": {},
            }

        # Extract achievements from portfolio if available
        achievements = []
        if profile.portfolio:
            achievements = profile.portfolio.get("achievements", [])

        return {
            "skills": profile.skills or [],
            "experience_years": profile.experience_years or 0,
            "job_title": profile.job_title or profile.profession or "Professional",
            "certifications": profile.certifications or [],
            "achievements": achievements,
            "portfolio": profile.portfolio or {},
            "preferred_industries": profile.preferred_industries,
        }

    def _build_prompt(
        self,
        job_context: Dict[str, Any],
        profile_context: Dict[str, Any],
        tone_config: Dict[str, str],
        additional_context: Optional[str] = None,
    ) -> str:
        """Build the generation prompt."""
        prompt_parts = [
            f"Generate a {tone_config['length']} proposal for this position.",
            "",
            "JOB DETAILS:",
            f"Position: {job_context.get('title', 'Unknown')}",
            f"Company: {job_context.get('company', 'Unknown')}",
        ]

        if job_context.get("required_skills"):
            prompt_parts.append(
                f"Required Skills: {', '.join(job_context['required_skills'][:10])}"
            )

        if job_context.get("key_requirements"):
            prompt_parts.append(
                f"Key Requirements: {', '.join(job_context['key_requirements'][:5])}"
            )

        if job_context.get("keywords"):
            prompt_parts.append(
                f"Keywords to use naturally: {', '.join(job_context['keywords'][:8])}"
            )

        prompt_parts.extend(
            [
                "",
                "CANDIDATE PROFILE:",
                f"Role: {profile_context.get('job_title', 'Professional')}",
                f"Experience: {profile_context.get('experience_years', 0)} years",
            ]
        )

        if profile_context.get("skills"):
            prompt_parts.append(
                f"Relevant Skills: {', '.join(profile_context['skills'][:10])}"
            )

        if profile_context.get("certifications"):
            prompt_parts.append(
                f"Certifications: {', '.join(profile_context['certifications'][:3])}"
            )

        if profile_context.get("achievements"):
            prompt_parts.append(
                f"Key Achievements: {', '.join(profile_context['achievements'][:3])}"
            )

        prompt_parts.extend(
            [
                "",
                "TONE INSTRUCTIONS:",
                f"Length: {tone_config['length']}",
                f"Style: {tone_config['style']}",
                f"Focus: {tone_config['focus']}",
            ]
        )

        if additional_context:
            prompt_parts.extend(
                [
                    "",
                    "ADDITIONAL CONTEXT FROM USER:",
                    additional_context,
                ]
            )

        prompt_parts.extend(
            [
                "",
                "Write the proposal now. Return ONLY the proposal text, no headers or explanations.",
            ]
        )

        return "\n".join(prompt_parts)

    def _format_job_context(self, job_context: Dict[str, Any]) -> str:
        """Format job context for prompts."""
        lines = [
            f"Position: {job_context.get('title', 'Unknown')}",
            f"Company: {job_context.get('company', 'Unknown')}",
        ]
        if job_context.get("required_skills"):
            lines.append(f"Skills: {', '.join(job_context['required_skills'][:8])}")
        return "\n".join(lines)

    def _extract_used_keywords(
        self, proposal: str, keywords: List[str]
    ) -> List[str]:
        """Extract which keywords were used in the proposal."""
        proposal_lower = proposal.lower()
        return [kw for kw in keywords if kw.lower() in proposal_lower]

    def _extract_highlighted_experience(
        self, proposal: str, achievements: List[str]
    ) -> List[str]:
        """Extract which achievements were mentioned in the proposal."""
        proposal_lower = proposal.lower()
        highlighted = []
        for achievement in achievements:
            # Check for significant overlap (not just single words)
            words = achievement.lower().split()
            if len(words) >= 3:
                # Check if at least half the words appear
                matches = sum(1 for w in words if w in proposal_lower)
                if matches >= len(words) // 2:
                    highlighted.append(achievement)
        return highlighted

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
