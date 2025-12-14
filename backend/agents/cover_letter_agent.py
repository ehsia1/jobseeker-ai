"""Cover Letter Agent - Generate tailored, ATS-optimized cover letters."""

import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from uuid import UUID
from enum import Enum

from langgraph.graph import StateGraph, END
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.models.job import Job
from backend.models.resume import Resume
from backend.models.user import UserProfile

logger = logging.getLogger(__name__)


class CoverLetterStyle(str, Enum):
    """Cover letter style options."""
    TRADITIONAL = "traditional"  # Formal, conservative industries
    MODERN = "modern"  # Contemporary, tech-friendly
    CREATIVE = "creative"  # Startups, creative industries
    EXECUTIVE = "executive"  # Senior/leadership roles


class CoverLetterLength(str, Enum):
    """Cover letter length options."""
    CONCISE = "concise"  # 200-250 words
    STANDARD = "standard"  # 300-400 words
    DETAILED = "detailed"  # 450-550 words


class CoverLetterState(TypedDict):
    """State for cover letter generation workflow."""
    user_id: str
    job_id: Optional[str]
    job_description: Optional[str]
    style: str
    length: str
    include_salary_expectations: bool
    emphasize_remote: bool

    # Loaded data
    resume_data: Optional[Dict[str, Any]]
    profile_data: Optional[Dict[str, Any]]
    job_data: Optional[Dict[str, Any]]

    # Analysis results
    skill_alignment: Dict[str, Any]
    keyword_analysis: Dict[str, Any]
    experience_matches: List[Dict[str, Any]]

    # Generated content
    cover_letter: str
    ats_score: int
    keywords_used: List[str]
    keywords_missing: List[str]
    suggestions: List[str]

    # Metadata
    messages: List[str]
    errors: List[str]


# Style-specific instructions for the LLM
STYLE_INSTRUCTIONS = {
    CoverLetterStyle.TRADITIONAL: {
        "tone": "Formal and professional",
        "structure": "Classic three-paragraph format with formal salutation",
        "language": "Conservative vocabulary, avoid contractions, use 'Dear Hiring Manager'",
        "suitable_for": "Banking, law, government, healthcare, established corporations"
    },
    CoverLetterStyle.MODERN: {
        "tone": "Professional yet conversational",
        "structure": "Clear sections with a hook opening, story-driven body",
        "language": "Direct, results-focused, slight personality allowed",
        "suitable_for": "Tech companies, modern enterprises, digital agencies"
    },
    CoverLetterStyle.CREATIVE: {
        "tone": "Engaging and personable",
        "structure": "Flexible format, can start with a compelling story or question",
        "language": "Creative vocabulary, personality-driven, memorable opening",
        "suitable_for": "Startups, creative agencies, marketing, design roles"
    },
    CoverLetterStyle.EXECUTIVE: {
        "tone": "Strategic and leadership-focused",
        "structure": "Achievement-led format emphasizing impact and vision",
        "language": "Executive vocabulary, focus on ROI, team building, strategic outcomes",
        "suitable_for": "C-suite, VP roles, Director positions, senior management"
    }
}

LENGTH_INSTRUCTIONS = {
    CoverLetterLength.CONCISE: {
        "word_range": "200-250 words",
        "paragraphs": "2-3 tight paragraphs",
        "guidance": "Focus only on the most compelling qualifications"
    },
    CoverLetterLength.STANDARD: {
        "word_range": "300-400 words",
        "paragraphs": "3-4 well-developed paragraphs",
        "guidance": "Balance between depth and brevity"
    },
    CoverLetterLength.DETAILED: {
        "word_range": "450-550 words",
        "paragraphs": "4-5 comprehensive paragraphs",
        "guidance": "Include specific examples and achievements with context"
    }
}


class CoverLetterAgent:
    """Agent for generating tailored, ATS-optimized cover letters."""

    SYSTEM_PROMPT = """You are an expert cover letter writer with deep knowledge of ATS systems and hiring practices.

Your cover letters are:
- Tailored specifically to the job and company
- ATS-optimized with natural keyword integration
- Achievement-focused with quantified results
- Engaging from the first sentence
- Professional yet human-sounding

Structure guidelines:
1. Opening: Hook + specific interest in this role/company
2. Body: 2-3 relevant achievements that match their needs
3. Connection: How your experience solves their problems
4. Close: Clear call-to-action and enthusiasm

Avoid:
- Generic openings ("I am writing to apply...")
- Repeating your resume verbatim
- Overused phrases ("team player", "hard worker", "passionate")
- Vague claims without evidence
- Excessive flattery or desperation

ATS Rules:
- Include exact keywords from job description naturally
- Use standard section headers if applicable
- Avoid tables, graphics, or unusual formatting
- Spell out acronyms once before abbreviating"""

    def __init__(self, db: AsyncSession):
        """Initialize the Cover Letter Agent.

        Args:
            db: Async database session
        """
        self.db = db
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(CoverLetterState)

        # Add nodes
        workflow.add_node("load_data", self._load_data_node)
        workflow.add_node("analyze_alignment", self._analyze_alignment_node)
        workflow.add_node("extract_keywords", self._extract_keywords_node)
        workflow.add_node("match_experience", self._match_experience_node)
        workflow.add_node("generate_letter", self._generate_letter_node)
        workflow.add_node("calculate_ats_score", self._calculate_ats_score_node)
        workflow.add_node("generate_suggestions", self._generate_suggestions_node)

        # Define edges
        workflow.set_entry_point("load_data")
        workflow.add_edge("load_data", "analyze_alignment")
        workflow.add_edge("analyze_alignment", "extract_keywords")
        workflow.add_edge("extract_keywords", "match_experience")
        workflow.add_edge("match_experience", "generate_letter")
        workflow.add_edge("generate_letter", "calculate_ats_score")
        workflow.add_edge("calculate_ats_score", "generate_suggestions")
        workflow.add_edge("generate_suggestions", END)

        return workflow.compile()

    async def _load_data_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Load user resume, profile, and job data."""
        logger.info(f"Loading data for user {state['user_id']}")
        state["messages"].append("Loading your profile and resume...")

        try:
            # Load resume with work experiences
            resume_result = await self.db.execute(
                select(Resume)
                .options(selectinload(Resume.work_experiences))
                .where(Resume.user_id == state["user_id"])
            )
            resume = resume_result.scalar_one_or_none()

            if resume:
                work_experiences = []
                for exp in resume.work_experiences:
                    # Check if end_date is None (current position)
                    is_current = exp.end_date is None
                    work_experiences.append({
                        "job_title": exp.title,  # Use 'title' attribute
                        "company": exp.company,  # Use 'company' attribute
                        "start_date": exp.start_date.isoformat() if exp.start_date else None,
                        "end_date": exp.end_date.isoformat() if exp.end_date else None,
                        "is_current": is_current,
                        "description": exp.description,
                        "achievements": exp.achievements or [],
                        "skills_used": exp.skills_used or [],
                    })

                state["resume_data"] = {
                    "full_name": resume.full_name,
                    "email": resume.email,
                    "phone": resume.phone,
                    "location": resume.location,
                    "summary": resume.summary,
                    "skills": resume.skills or [],
                    "education": resume.education or [],
                    "certifications": resume.certifications or [],
                    "work_experiences": work_experiences,
                }
                state["messages"].append(f"Resume loaded: {resume.full_name}")
            else:
                state["resume_data"] = None
                state["messages"].append("No resume found - using profile data only")

            # Load user profile
            profile_result = await self.db.execute(
                select(UserProfile).where(UserProfile.user_id == state["user_id"])
            )
            profile = profile_result.scalar_one_or_none()

            if profile:
                state["profile_data"] = {
                    "profession": profile.profession,
                    "job_title": profile.job_title,
                    "skills": profile.skills or [],
                    "experience_years": profile.experience_years,
                    "certifications": profile.certifications or [],
                    "portfolio": profile.portfolio or {},
                    "preferred_industries": profile.preferred_industries or [],
                }
                state["messages"].append("Profile loaded")
            else:
                state["profile_data"] = None

            # Load job if job_id provided
            if state.get("job_id"):
                job_result = await self.db.execute(
                    select(Job).where(Job.id == state["job_id"])
                )
                job = job_result.scalar_one_or_none()

                if job:
                    state["job_data"] = {
                        "id": str(job.id),
                        "title": job.title,
                        "company": job.company,
                        "description": job.description,
                        "requirements": job.requirements or [],
                        "skills": job.skills or [],
                        "location": job.location,
                        "remote": job.remote,
                        "salary_min": float(job.rate_min) if job.rate_min else None,
                        "salary_max": float(job.rate_max) if job.rate_max else None,
                    }
                    state["messages"].append(f"Job loaded: {job.title} at {job.company}")
            elif state.get("job_description"):
                # Parse job description text
                state["job_data"] = self._parse_job_description(state["job_description"])
                state["messages"].append("Job description parsed")

            return state

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            state["errors"].append(f"Failed to load data: {str(e)}")
            return state

    def _parse_job_description(self, jd_text: str) -> Dict[str, Any]:
        """Parse a raw job description into structured data."""
        # Simple extraction - in production, could use LLM or JD parser service
        lines = jd_text.strip().split('\n')
        title = lines[0] if lines else "Position"

        # Extract potential skills (words that look like technologies)
        common_skills = [
            'python', 'javascript', 'typescript', 'react', 'node', 'sql', 'postgresql',
            'mongodb', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'api',
            'rest', 'graphql', 'agile', 'scrum', 'ci/cd', 'fastapi', 'django', 'flask'
        ]

        jd_lower = jd_text.lower()
        found_skills = [skill for skill in common_skills if skill in jd_lower]

        return {
            "title": title,
            "company": "the company",
            "description": jd_text,
            "requirements": [],
            "skills": found_skills,
            "location": None,
            "remote": 'remote' in jd_lower,
        }

    async def _analyze_alignment_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Analyze skill and experience alignment between candidate and job."""
        logger.info("Analyzing skill alignment")
        state["messages"].append("Analyzing skill alignment...")

        try:
            job_data = state.get("job_data") or {}
            job_skills = set(s.lower() for s in job_data.get("skills", []))

            # Get user skills from both resume and profile
            user_skills = set()
            if state.get("resume_data"):
                user_skills.update(s.lower() for s in state["resume_data"].get("skills", []))
            if state.get("profile_data"):
                user_skills.update(s.lower() for s in state["profile_data"].get("skills", []))

            # Calculate alignment
            matching_skills = job_skills & user_skills
            missing_skills = job_skills - user_skills
            extra_skills = user_skills - job_skills

            match_percentage = (len(matching_skills) / len(job_skills) * 100) if job_skills else 0

            state["skill_alignment"] = {
                "matching_skills": list(matching_skills),
                "missing_skills": list(missing_skills),
                "additional_skills": list(extra_skills)[:10],  # Limit extra skills shown
                "match_percentage": round(match_percentage, 1),
                "alignment_level": self._get_alignment_level(match_percentage),
            }

            state["messages"].append(
                f"Skill alignment: {match_percentage:.0f}% ({len(matching_skills)} matching skills)"
            )

            return state

        except Exception as e:
            logger.error(f"Error analyzing alignment: {e}")
            state["errors"].append(f"Alignment analysis failed: {str(e)}")
            state["skill_alignment"] = {"matching_skills": [], "missing_skills": [], "match_percentage": 0}
            return state

    def _get_alignment_level(self, percentage: float) -> str:
        """Get alignment level description."""
        if percentage >= 80:
            return "excellent"
        elif percentage >= 60:
            return "strong"
        elif percentage >= 40:
            return "moderate"
        else:
            return "developing"

    async def _extract_keywords_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Extract important keywords from job description for ATS optimization."""
        logger.info("Extracting keywords for ATS optimization")
        state["messages"].append("Extracting keywords for ATS optimization...")

        try:
            job_data = state.get("job_data") or {}
            description = job_data.get("description", "")

            # Keywords to look for (common ATS-important terms)
            keyword_categories = {
                "technical_skills": state.get("skill_alignment", {}).get("matching_skills", []),
                "soft_skills": [],
                "action_verbs": [],
                "industry_terms": [],
            }

            # Extract soft skills
            soft_skills = [
                'leadership', 'communication', 'collaboration', 'problem-solving',
                'analytical', 'strategic', 'creative', 'detail-oriented', 'self-motivated',
                'team player', 'cross-functional', 'stakeholder', 'deadline'
            ]
            desc_lower = description.lower()
            keyword_categories["soft_skills"] = [s for s in soft_skills if s in desc_lower]

            # Extract action verbs
            action_verbs = [
                'develop', 'implement', 'design', 'manage', 'lead', 'create',
                'build', 'optimize', 'analyze', 'collaborate', 'deliver', 'drive',
                'execute', 'maintain', 'improve', 'architect', 'scale'
            ]
            keyword_categories["action_verbs"] = [v for v in action_verbs if v in desc_lower]

            # All important keywords combined
            all_keywords = (
                keyword_categories["technical_skills"] +
                keyword_categories["soft_skills"] +
                keyword_categories["action_verbs"]
            )

            state["keyword_analysis"] = {
                "categories": keyword_categories,
                "all_keywords": list(set(all_keywords)),
                "priority_keywords": all_keywords[:15],  # Top 15 to focus on
            }

            state["messages"].append(f"Extracted {len(all_keywords)} important keywords")

            return state

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            state["errors"].append(f"Keyword extraction failed: {str(e)}")
            state["keyword_analysis"] = {"all_keywords": [], "priority_keywords": []}
            return state

    async def _match_experience_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Match user experiences with job requirements."""
        logger.info("Matching experiences to job requirements")
        state["messages"].append("Finding relevant experiences...")

        try:
            job_data = state.get("job_data") or {}
            resume_data = state.get("resume_data") or {}

            job_skills = set(s.lower() for s in job_data.get("skills", []))
            job_description = job_data.get("description", "").lower()

            experience_matches = []

            for exp in resume_data.get("work_experiences", []):
                exp_skills = set(s.lower() for s in exp.get("skills_used", []))
                skill_overlap = job_skills & exp_skills

                # Check if experience description is relevant
                exp_desc = (exp.get("description", "") or "").lower()
                exp_achievements = exp.get("achievements", [])

                # Calculate relevance score
                relevance_score = len(skill_overlap) * 10

                # Boost for keyword matches in description
                for keyword in state.get("keyword_analysis", {}).get("priority_keywords", []):
                    if keyword.lower() in exp_desc:
                        relevance_score += 5

                if relevance_score > 0 or skill_overlap:
                    experience_matches.append({
                        "job_title": exp.get("job_title"),
                        "company": exp.get("company"),
                        "is_current": exp.get("is_current", False),
                        "matching_skills": list(skill_overlap),
                        "achievements": exp_achievements[:3],  # Top 3 achievements
                        "relevance_score": relevance_score,
                    })

            # Sort by relevance
            experience_matches.sort(key=lambda x: x["relevance_score"], reverse=True)

            state["experience_matches"] = experience_matches[:5]  # Top 5 most relevant

            if experience_matches:
                state["messages"].append(
                    f"Found {len(experience_matches)} relevant experiences"
                )
            else:
                state["messages"].append("No direct experience matches found")

            return state

        except Exception as e:
            logger.error(f"Error matching experiences: {e}")
            state["errors"].append(f"Experience matching failed: {str(e)}")
            state["experience_matches"] = []
            return state

    async def _generate_letter_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Generate the cover letter using LLM."""
        logger.info("Generating cover letter")
        state["messages"].append("Generating your personalized cover letter...")

        try:
            # Get style and length configs
            style = CoverLetterStyle(state.get("style", "modern"))
            length = CoverLetterLength(state.get("length", "standard"))

            style_config = STYLE_INSTRUCTIONS[style]
            length_config = LENGTH_INSTRUCTIONS[length]

            # Build the prompt
            prompt = self._build_generation_prompt(state, style_config, length_config)

            # Check if LLM is available
            if settings.openai_api_key or settings.anthropic_api_key:
                from backend.services.llm_service import get_llm_service
                llm_service = get_llm_service()

                response = await llm_service.generate(
                    prompt=prompt,
                    system_prompt=self.SYSTEM_PROMPT,
                )

                state["cover_letter"] = response.content.strip()
            else:
                # Fallback to template-based generation
                state["cover_letter"] = self._generate_template_letter(state, style_config, length_config)

            # Extract keywords used in the generated letter
            letter_lower = state["cover_letter"].lower()
            priority_keywords = state.get("keyword_analysis", {}).get("priority_keywords", [])

            state["keywords_used"] = [kw for kw in priority_keywords if kw.lower() in letter_lower]
            state["keywords_missing"] = [kw for kw in priority_keywords if kw.lower() not in letter_lower]

            state["messages"].append("Cover letter generated successfully")

            return state

        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            state["errors"].append(f"Generation failed: {str(e)}")
            state["cover_letter"] = ""
            return state

    def _build_generation_prompt(
        self,
        state: CoverLetterState,
        style_config: Dict[str, str],
        length_config: Dict[str, str]
    ) -> str:
        """Build the LLM prompt for cover letter generation."""
        job_data = state.get("job_data") or {}
        resume_data = state.get("resume_data") or {}
        profile_data = state.get("profile_data") or {}

        # Get candidate name
        candidate_name = resume_data.get("full_name", "")
        if not candidate_name and profile_data:
            candidate_name = profile_data.get("job_title", "Candidate")

        # Build experience section
        experience_text = ""
        for exp in state.get("experience_matches", [])[:3]:
            achievements = exp.get("achievements", [])
            achievement_text = "\n".join(f"  - {a}" for a in achievements[:2]) if achievements else ""
            experience_text += f"""
{exp.get('job_title')} at {exp.get('company')}
Relevant skills: {', '.join(exp.get('matching_skills', []))}
{achievement_text}
"""

        prompt = f"""Write a cover letter for the following position:

POSITION DETAILS:
- Title: {job_data.get('title', 'Position')}
- Company: {job_data.get('company', 'Company')}
- Remote: {'Yes' if job_data.get('remote') else 'On-site/Hybrid'}

JOB DESCRIPTION:
{job_data.get('description', '')[:2000]}

CANDIDATE INFORMATION:
- Name: {candidate_name}
- Current Role: {profile_data.get('job_title', resume_data.get('work_experiences', [{}])[0].get('job_title', 'Professional') if resume_data.get('work_experiences') else 'Professional')}
- Years of Experience: {profile_data.get('experience_years', 'Several')}
- Key Skills: {', '.join((resume_data.get('skills', []) or profile_data.get('skills', []))[:10])}

RELEVANT EXPERIENCE:
{experience_text if experience_text else 'Use general professional experience'}

KEYWORDS TO NATURALLY INCORPORATE:
{', '.join(state.get('keyword_analysis', {}).get('priority_keywords', [])[:12])}

STYLE REQUIREMENTS:
- Tone: {style_config['tone']}
- Structure: {style_config['structure']}
- Language: {style_config['language']}

LENGTH REQUIREMENTS:
- Word range: {length_config['word_range']}
- Paragraphs: {length_config['paragraphs']}
- Guidance: {length_config['guidance']}

SPECIAL INSTRUCTIONS:
{f'- Mention openness to remote work' if state.get('emphasize_remote') else ''}
{f'- Include salary expectations: ${job_data.get("salary_min", "negotiable")}-${job_data.get("salary_max", "")}' if state.get('include_salary_expectations') and job_data.get('salary_min') else ''}

Write the cover letter now. Return ONLY the letter text, properly formatted."""

        return prompt

    def _generate_template_letter(
        self,
        state: CoverLetterState,
        style_config: Dict[str, str],
        length_config: Dict[str, str]
    ) -> str:
        """Generate a template-based cover letter when LLM is unavailable."""
        job_data = state.get("job_data") or {}
        resume_data = state.get("resume_data") or {}
        profile_data = state.get("profile_data") or {}
        skill_alignment = state.get("skill_alignment") or {}

        candidate_name = resume_data.get("full_name", "[Your Name]")
        job_title = job_data.get("title", "the position")
        company = job_data.get("company", "your company")
        matching_skills = skill_alignment.get("matching_skills", [])[:5]
        experience_years = profile_data.get("experience_years", "several")

        # Get most relevant experience
        top_experience = state.get("experience_matches", [{}])[0] if state.get("experience_matches") else {}

        letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}. With {experience_years} years of experience and expertise in {', '.join(matching_skills[:3]) if matching_skills else 'relevant technologies'}, I am confident I would be a valuable addition to your team.

"""

        if top_experience:
            letter += f"""In my role as {top_experience.get('job_title', 'a professional')} at {top_experience.get('company', 'my previous company')}, I developed deep expertise in {', '.join(top_experience.get('matching_skills', matching_skills)[:3])}. """

            if top_experience.get('achievements'):
                letter += f"Key achievements include: {top_experience['achievements'][0]}. "

        letter += f"""
My technical background aligns well with your requirements, particularly in {', '.join(matching_skills[:4]) if matching_skills else 'the required areas'}. I am drawn to this opportunity because it offers the chance to contribute to {company}'s continued success while growing my skills in a collaborative environment.

I would welcome the opportunity to discuss how my experience and skills can benefit your team. Thank you for considering my application.

Best regards,
{candidate_name}"""

        return letter.strip()

    async def _calculate_ats_score_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Calculate ATS compatibility score."""
        logger.info("Calculating ATS compatibility score")
        state["messages"].append("Calculating ATS compatibility...")

        try:
            cover_letter = state.get("cover_letter", "")
            keywords_used = state.get("keywords_used", [])
            keywords_missing = state.get("keywords_missing", [])
            priority_keywords = state.get("keyword_analysis", {}).get("priority_keywords", [])

            # Calculate component scores
            keyword_score = (len(keywords_used) / len(priority_keywords) * 100) if priority_keywords else 100

            # Check formatting (penalize unusual characters)
            unusual_chars = sum(1 for c in cover_letter if c in '★☆•►▪︎')
            formatting_score = max(0, 100 - unusual_chars * 10)

            # Check length appropriateness
            word_count = len(cover_letter.split())
            length_score = 100
            if word_count < 150:
                length_score = 60  # Too short
            elif word_count > 600:
                length_score = 70  # Too long

            # Check for important structural elements
            structure_score = 100
            letter_lower = cover_letter.lower()
            if "dear" not in letter_lower and "hi" not in letter_lower:
                structure_score -= 15  # No salutation
            if "sincerely" not in letter_lower and "regards" not in letter_lower and "thank" not in letter_lower:
                structure_score -= 15  # No closing

            # Calculate overall score
            ats_score = int(
                keyword_score * 0.40 +
                formatting_score * 0.20 +
                length_score * 0.20 +
                structure_score * 0.20
            )

            state["ats_score"] = min(100, max(0, ats_score))

            state["messages"].append(f"ATS Score: {state['ats_score']}/100")

            return state

        except Exception as e:
            logger.error(f"Error calculating ATS score: {e}")
            state["errors"].append(f"ATS calculation failed: {str(e)}")
            state["ats_score"] = 0
            return state

    async def _generate_suggestions_node(self, state: CoverLetterState) -> Dict[str, Any]:
        """Generate improvement suggestions."""
        logger.info("Generating suggestions")

        try:
            suggestions = []

            # Keyword suggestions
            keywords_missing = state.get("keywords_missing", [])
            if keywords_missing:
                suggestions.append(
                    f"Consider adding these keywords: {', '.join(keywords_missing[:5])}"
                )

            # ATS score suggestions
            ats_score = state.get("ats_score", 0)
            if ats_score < 70:
                suggestions.append(
                    "Your ATS score is below optimal. Try incorporating more exact keywords from the job description."
                )

            # Length suggestions
            word_count = len(state.get("cover_letter", "").split())
            if word_count < 200:
                suggestions.append(
                    "Consider expanding with specific achievements or examples."
                )
            elif word_count > 500:
                suggestions.append(
                    "Consider condensing to focus on your most relevant qualifications."
                )

            # Skill alignment suggestions
            alignment = state.get("skill_alignment", {})
            if alignment.get("match_percentage", 0) < 50:
                missing = alignment.get("missing_skills", [])[:3]
                if missing:
                    suggestions.append(
                        f"To improve your match, consider highlighting transferable skills related to: {', '.join(missing)}"
                    )

            state["suggestions"] = suggestions
            state["messages"].append("Analysis complete")

            return state

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            state["errors"].append(f"Suggestion generation failed: {str(e)}")
            state["suggestions"] = []
            return state

    async def run(
        self,
        user_id: str,
        job_id: Optional[str] = None,
        job_description: Optional[str] = None,
        style: str = "modern",
        length: str = "standard",
        include_salary_expectations: bool = False,
        emphasize_remote: bool = False,
    ) -> Dict[str, Any]:
        """Run the cover letter generation agent.

        Args:
            user_id: User ID
            job_id: Optional job ID from database
            job_description: Optional raw job description text
            style: Cover letter style (traditional, modern, creative, executive)
            length: Cover letter length (concise, standard, detailed)
            include_salary_expectations: Whether to mention salary
            emphasize_remote: Whether to emphasize remote work preference

        Returns:
            Dictionary with cover letter and metadata
        """
        if not job_id and not job_description:
            return {
                "success": False,
                "error": "Either job_id or job_description must be provided",
            }

        initial_state: CoverLetterState = {
            "user_id": user_id,
            "job_id": job_id,
            "job_description": job_description,
            "style": style,
            "length": length,
            "include_salary_expectations": include_salary_expectations,
            "emphasize_remote": emphasize_remote,
            "resume_data": None,
            "profile_data": None,
            "job_data": None,
            "skill_alignment": {},
            "keyword_analysis": {},
            "experience_matches": [],
            "cover_letter": "",
            "ats_score": 0,
            "keywords_used": [],
            "keywords_missing": [],
            "suggestions": [],
            "messages": [],
            "errors": [],
        }

        try:
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)

            return {
                "success": True,
                "cover_letter": final_state.get("cover_letter", ""),
                "style": style,
                "length": length,
                "word_count": len(final_state.get("cover_letter", "").split()),
                "ats_score": final_state.get("ats_score", 0),
                "skill_alignment": final_state.get("skill_alignment", {}),
                "keywords_used": final_state.get("keywords_used", []),
                "keywords_missing": final_state.get("keywords_missing", []),
                "experience_matches": final_state.get("experience_matches", []),
                "suggestions": final_state.get("suggestions", []),
                "job_data": {
                    "title": final_state.get("job_data", {}).get("title"),
                    "company": final_state.get("job_data", {}).get("company"),
                },
                "messages": final_state.get("messages", []),
                "errors": final_state.get("errors", []),
            }

        except Exception as e:
            logger.error(f"Cover Letter agent failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": initial_state["messages"],
                "errors": initial_state["errors"] + [str(e)],
            }

    async def regenerate_with_feedback(
        self,
        user_id: str,
        original_letter: str,
        feedback: str,
        job_id: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Regenerate cover letter incorporating user feedback.

        Args:
            user_id: User ID
            original_letter: The original generated letter
            feedback: User's feedback/requested changes
            job_id: Optional job ID
            job_description: Optional job description

        Returns:
            Updated cover letter with metadata
        """
        try:
            if settings.openai_api_key or settings.anthropic_api_key:
                from backend.services.llm_service import get_llm_service
                llm_service = get_llm_service()

                prompt = f"""Revise this cover letter based on the user's feedback.

ORIGINAL LETTER:
{original_letter}

USER FEEDBACK:
{feedback}

INSTRUCTIONS:
- Apply the requested changes while maintaining professional quality
- Keep the overall structure and flow intact
- Preserve keywords and ATS optimization
- Return ONLY the revised letter, no explanations

Write the revised letter now:"""

                response = await llm_service.generate(
                    prompt=prompt,
                    system_prompt=self.SYSTEM_PROMPT,
                )

                revised_letter = response.content.strip()

                return {
                    "success": True,
                    "cover_letter": revised_letter,
                    "word_count": len(revised_letter.split()),
                    "feedback_applied": feedback,
                }
            else:
                return {
                    "success": False,
                    "error": "LLM service required for feedback-based regeneration",
                }

        except Exception as e:
            logger.error(f"Regeneration failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
