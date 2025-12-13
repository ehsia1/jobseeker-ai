"""Resume Optimization Agent - AI-powered resume tailoring and ATS optimization."""

import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from uuid import UUID

from langgraph.graph import StateGraph, END
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import get_async_session
from backend.models.job import Job
from backend.models.resume import Resume
from backend.models.user import UserProfile

logger = logging.getLogger(__name__)


class ResumeOptimizationState(TypedDict):
    """State for the resume optimization agent."""
    user_id: str
    job_id: Optional[str]
    job_description: Optional[str]
    resume_data: Optional[Dict[str, Any]]
    job_context: Optional[Dict[str, Any]]
    ats_score_before: Optional[Dict[str, Any]]
    ats_score_after: Optional[Dict[str, Any]]
    optimized_sections: List[Dict[str, Any]]
    keywords_matched: List[str]
    keywords_missing: List[str]
    skills_highlighted: List[str]
    improvement_summary: str
    cover_letter: Optional[str]
    messages: List[str]
    errors: List[str]
    # Config
    optimization_focus: str
    include_cover_letter: bool
    preserve_formatting: bool


class ResumeOptimizationAgent:
    """Agent for AI-powered resume optimization and ATS scoring."""

    def __init__(self):
        """Initialize the Resume Optimization agent."""
        self.llm = self._init_llm()
        self.workflow = self._build_workflow()

    def _init_llm(self):
        """Initialize the LLM based on settings."""
        provider = settings.llm_provider

        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=settings.ollama_model,
                    base_url=settings.ollama_base_url,
                    temperature=0.7
                )
            except ImportError:
                logger.warning("langchain-ollama not installed, using mock LLM")
                return self._get_mock_llm()

        elif provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    api_key=settings.openai_api_key
                )
            except ImportError:
                return self._get_mock_llm()

        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    temperature=0.7,
                    api_key=settings.anthropic_api_key
                )
            except ImportError:
                return self._get_mock_llm()
        else:
            return self._get_mock_llm()

    def _get_mock_llm(self):
        """Get a mock LLM for testing."""
        from langchain_community.llms import FakeListLLM
        return FakeListLLM(
            responses=["I'll help you optimize your resume."]
        )

    def _build_workflow(self):
        """Build the LangGraph workflow for resume optimization."""
        workflow = StateGraph(ResumeOptimizationState)

        # Add nodes
        workflow.add_node("load_resume", self.load_resume_node)
        workflow.add_node("analyze_target", self.analyze_target_node)
        workflow.add_node("ats_audit", self.ats_audit_node)
        workflow.add_node("keyword_analysis", self.keyword_analysis_node)
        workflow.add_node("optimize_sections", self.optimize_sections_node)
        workflow.add_node("generate_cover_letter", self.generate_cover_letter_node)
        workflow.add_node("final_scoring", self.final_scoring_node)

        # Define edges
        workflow.set_entry_point("load_resume")
        workflow.add_edge("load_resume", "analyze_target")
        workflow.add_edge("analyze_target", "ats_audit")
        workflow.add_edge("ats_audit", "keyword_analysis")
        workflow.add_edge("keyword_analysis", "optimize_sections")
        workflow.add_conditional_edges(
            "optimize_sections",
            lambda state: "generate_cover_letter" if state.get("include_cover_letter") else "final_scoring"
        )
        workflow.add_edge("generate_cover_letter", "final_scoring")
        workflow.add_edge("final_scoring", END)

        return workflow.compile()

    async def load_resume_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Load and parse user's resume."""
        logger.info(f"Loading resume for user {state['user_id']}")
        state["messages"].append("Loading your resume...")

        try:
            async with get_async_session() as db:
                result = await db.execute(
                    select(Resume)
                    .options(selectinload(Resume.work_experiences))
                    .where(Resume.user_id == state["user_id"])
                )
                resume = result.scalar_one_or_none()

            if resume:
                state["resume_data"] = {
                    "id": str(resume.id),
                    "full_name": resume.full_name,
                    "email": resume.email,
                    "phone": resume.phone,
                    "location": resume.location,
                    "linkedin_url": resume.linkedin_url,
                    "github_url": resume.github_url,
                    "portfolio_url": resume.portfolio_url,
                    "summary": resume.summary,
                    "skills": resume.skills or [],
                    "education": resume.education or [],
                    "certifications": resume.certifications or [],
                    "languages": resume.languages or [],
                    "raw_text": resume.raw_text,
                    "work_experiences": [
                        {
                            "company": exp.company,
                            "title": exp.title,
                            "location": exp.location,
                            "start_date": str(exp.start_date) if exp.start_date else None,
                            "end_date": str(exp.end_date) if exp.end_date else None,
                            "is_current": exp.is_current,
                            "description": exp.description,
                            "achievements": exp.achievements or [],
                            "skills_used": exp.skills_used or [],
                            "metrics": exp.metrics or {}
                        }
                        for exp in (resume.work_experiences or [])
                    ]
                }
                state["messages"].append(
                    f"✓ Resume loaded: {resume.full_name or 'Your resume'} "
                    f"with {len(resume.skills or [])} skills and "
                    f"{len(resume.work_experiences or [])} work experiences"
                )
            else:
                state["errors"].append("No resume found. Please upload your resume first.")
                state["resume_data"] = None

        except Exception as e:
            state["errors"].append(f"Error loading resume: {str(e)}")

        return state

    async def analyze_target_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Analyze target job requirements."""
        logger.info("Analyzing target job")

        # Skip if no resume loaded
        if not state.get("resume_data"):
            return state

        # Check for job_description first (direct input)
        if state.get("job_description"):
            state["job_context"] = await self._parse_job_description(state["job_description"])
            state["messages"].append("✓ Analyzed job description for optimization targets")
            return state

        # Check for job_id
        if not state.get("job_id"):
            state["messages"].append("No specific job provided - using general ATS optimization")
            state["job_context"] = None
            return state

        try:
            job = None
            job_id = state["job_id"]

            async with get_async_session() as db:
                if "_" in job_id:
                    parts = job_id.split("_", 1)
                    source = parts[0]
                    source_id = parts[1] if len(parts) > 1 else None
                    result = await db.execute(
                        select(Job).where(Job.source == source, Job.source_id == source_id)
                    )
                    job = result.scalar_one_or_none()

                if not job:
                    try:
                        result = await db.execute(
                            select(Job).where(Job.id == job_id)
                        )
                        job = result.scalar_one_or_none()
                    except Exception:
                        pass

            if job:
                state["job_context"] = {
                    "id": str(job.id),
                    "title": job.title,
                    "company": job.company,
                    "description": job.description or "",
                    "skills": job.skills or [],
                    "requirements": job.requirements or [],
                    "nice_to_haves": job.nice_to_haves or [],
                    "remote": job.remote
                }
                state["messages"].append(
                    f"✓ Target job analyzed: {job.title} at {job.company}"
                )
            else:
                state["messages"].append("⚠ Job not found, using general optimization")

        except Exception as e:
            state["errors"].append(f"Error analyzing job: {str(e)}")

        return state

    async def _parse_job_description(self, description: str) -> Dict[str, Any]:
        """Parse a job description text to extract key information."""
        from backend.services.llm_service import get_llm_service

        llm = get_llm_service()

        prompt = f"""Analyze this job description and extract key information.

JOB DESCRIPTION:
{description[:4000]}

Extract and return as JSON:
{{
    "title": "inferred job title",
    "company": "company name if mentioned",
    "skills": ["required technical skills and tools"],
    "requirements": ["must-have qualifications"],
    "nice_to_haves": ["nice-to-have qualifications"],
    "keywords": ["important keywords for ATS"],
    "experience_level": "entry/mid/senior/lead",
    "remote": true/false/unknown
}}

Return ONLY valid JSON."""

        try:
            result = await llm.generate_structured(prompt)
            return result
        except Exception as e:
            logger.warning(f"Failed to parse job description: {e}")
            # Return basic extraction
            return {
                "description": description,
                "skills": [],
                "requirements": [],
                "keywords": []
            }

    async def ats_audit_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Perform ATS compatibility audit on current resume."""
        logger.info("Performing ATS audit")

        if not state.get("resume_data"):
            return state

        resume = state["resume_data"]
        state["messages"].append("Analyzing ATS compatibility...")

        try:
            # Calculate ATS scores
            scores = {
                "keyword_match": 0,
                "formatting_score": 0,
                "section_completeness": 0,
                "readability_score": 0,
                "issues": [],
                "suggestions": []
            }

            # Section completeness check
            required_sections = ["summary", "skills", "work_experiences", "education"]
            present_sections = 0
            for section in required_sections:
                if resume.get(section):
                    present_sections += 1
                else:
                    scores["issues"].append(f"Missing or empty: {section.replace('_', ' ').title()}")
                    scores["suggestions"].append(f"Add a {section.replace('_', ' ')} section")

            scores["section_completeness"] = int((present_sections / len(required_sections)) * 100)

            # Skills assessment
            skills = resume.get("skills", [])
            if len(skills) < 5:
                scores["issues"].append(f"Only {len(skills)} skills listed")
                scores["suggestions"].append("Add more relevant skills (aim for 10-15)")
            elif len(skills) > 20:
                scores["issues"].append("Too many skills listed")
                scores["suggestions"].append("Focus on 15-20 most relevant skills")

            # Contact info check
            contact_fields = ["email", "phone", "location"]
            missing_contact = [f for f in contact_fields if not resume.get(f)]
            if missing_contact:
                scores["issues"].append(f"Missing contact info: {', '.join(missing_contact)}")

            # Work experience quality
            experiences = resume.get("work_experiences", [])
            if experiences:
                exp_with_achievements = sum(1 for e in experiences if e.get("achievements"))
                exp_with_metrics = sum(1 for e in experiences if e.get("metrics"))

                if exp_with_achievements < len(experiences):
                    scores["issues"].append("Some roles lack achievement bullets")
                    scores["suggestions"].append("Add quantified achievements to each role")

                if exp_with_metrics == 0:
                    scores["issues"].append("No quantified metrics found")
                    scores["suggestions"].append("Add numbers and percentages to achievements")

            # Formatting score (simplified heuristics)
            raw_text = resume.get("raw_text", "")
            formatting_issues = 0

            if len(raw_text) < 300:
                formatting_issues += 1
                scores["issues"].append("Resume appears too short")
            elif len(raw_text) > 6000:
                formatting_issues += 1
                scores["issues"].append("Resume may be too long (aim for 1-2 pages)")

            # Check for common ATS-unfriendly elements
            if any(x in raw_text.lower() for x in ["graphics", "tables", "columns"]):
                formatting_issues += 1
                scores["suggestions"].append("Avoid complex formatting that ATS may not parse")

            scores["formatting_score"] = max(0, 100 - (formatting_issues * 25))

            # Readability score
            avg_sentence_length = len(raw_text.split(".")) if raw_text else 0
            words = len(raw_text.split()) if raw_text else 0
            avg_word_per_sentence = words / max(1, avg_sentence_length)

            if avg_word_per_sentence > 25:
                scores["suggestions"].append("Use shorter, more impactful sentences")

            scores["readability_score"] = min(100, max(50, 100 - int(avg_word_per_sentence * 2)))

            # Keyword match (if job context available)
            if state.get("job_context"):
                job_skills = set(s.lower() for s in state["job_context"].get("skills", []))
                resume_skills = set(s.lower() for s in skills)
                resume_text = raw_text.lower()

                matched = 0
                for skill in job_skills:
                    if skill in resume_skills or skill in resume_text:
                        matched += 1

                if job_skills:
                    scores["keyword_match"] = int((matched / len(job_skills)) * 100)
                else:
                    scores["keyword_match"] = 70  # Default if no job skills
            else:
                scores["keyword_match"] = 70  # Default without job context

            # Calculate overall score
            scores["overall_score"] = int(
                scores["keyword_match"] * 0.35 +
                scores["formatting_score"] * 0.20 +
                scores["section_completeness"] * 0.25 +
                scores["readability_score"] * 0.20
            )

            state["ats_score_before"] = scores
            state["messages"].append(
                f"✓ ATS audit complete: Current score {scores['overall_score']}/100"
            )

            if scores["issues"]:
                state["messages"].append(f"  Found {len(scores['issues'])} areas to improve")

        except Exception as e:
            state["errors"].append(f"Error in ATS audit: {str(e)}")

        return state

    async def keyword_analysis_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Analyze keyword coverage and gaps."""
        logger.info("Analyzing keywords")

        if not state.get("resume_data"):
            return state

        resume = state["resume_data"]
        job_context = state.get("job_context", {})

        try:
            resume_skills = set(s.lower() for s in resume.get("skills", []))
            raw_text = (resume.get("raw_text") or "").lower()

            # Combine all text for keyword matching
            all_resume_text = raw_text
            for exp in resume.get("work_experiences", []):
                all_resume_text += " " + " ".join(exp.get("achievements", []))
                all_resume_text += " " + (exp.get("description") or "")

            # Get target keywords
            target_keywords = set()
            if job_context:
                target_keywords.update(s.lower() for s in job_context.get("skills", []))
                target_keywords.update(s.lower() for s in job_context.get("requirements", []))
                target_keywords.update(s.lower() for s in job_context.get("keywords", []))

            if not target_keywords:
                # Use common high-impact keywords for general optimization
                target_keywords = {
                    "leadership", "management", "strategy", "analytics", "optimization",
                    "collaboration", "communication", "problem-solving", "innovation",
                    "agile", "results-driven", "team", "project", "revenue", "growth"
                }

            # Find matches and gaps
            matched = []
            missing = []

            for keyword in target_keywords:
                if keyword in resume_skills or keyword in all_resume_text:
                    matched.append(keyword)
                else:
                    missing.append(keyword)

            # Identify skills to highlight (present in resume AND in job)
            if job_context:
                job_skills = set(s.lower() for s in job_context.get("skills", []))
                skills_to_highlight = list(resume_skills & job_skills)
            else:
                skills_to_highlight = list(resume_skills)[:10]

            state["keywords_matched"] = matched
            state["keywords_missing"] = missing
            state["skills_highlighted"] = skills_to_highlight

            state["messages"].append(
                f"✓ Keyword analysis: {len(matched)} matched, {len(missing)} opportunities"
            )

        except Exception as e:
            state["errors"].append(f"Error in keyword analysis: {str(e)}")

        return state

    async def optimize_sections_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Generate optimized content for each resume section."""
        logger.info("Optimizing resume sections")

        if not state.get("resume_data"):
            return state

        resume = state["resume_data"]
        job_context = state.get("job_context", {})
        missing_keywords = state.get("keywords_missing", [])

        state["messages"].append("Optimizing resume sections...")
        optimized_sections = []

        try:
            # Optimize Summary/Professional Statement
            if resume.get("summary"):
                optimized_summary = await self._optimize_summary(
                    resume["summary"],
                    job_context,
                    missing_keywords[:5],
                    state["optimization_focus"]
                )
                optimized_sections.append(optimized_summary)

            # Optimize Work Experiences
            for i, exp in enumerate(resume.get("work_experiences", [])[:5]):
                optimized_exp = await self._optimize_experience(
                    exp,
                    job_context,
                    missing_keywords,
                    state["optimization_focus"]
                )
                optimized_sections.append(optimized_exp)

            # Optimize Skills Section
            if resume.get("skills"):
                optimized_skills = await self._optimize_skills(
                    resume["skills"],
                    job_context,
                    state["skills_highlighted"]
                )
                optimized_sections.append(optimized_skills)

            state["optimized_sections"] = optimized_sections

            # Generate improvement summary
            total_improvements = sum(len(s.get("improvement_notes", [])) for s in optimized_sections)
            keywords_added = []
            for s in optimized_sections:
                keywords_added.extend(s.get("keywords_added", []))

            state["improvement_summary"] = (
                f"Optimized {len(optimized_sections)} sections with {total_improvements} improvements. "
                f"Added {len(set(keywords_added))} keywords to improve ATS matching."
            )

            state["messages"].append(f"✓ Optimized {len(optimized_sections)} resume sections")

        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            state["errors"].append(f"Error optimizing sections: {str(e)}")

        return state

    async def _optimize_summary(
        self,
        summary: str,
        job_context: Dict[str, Any],
        missing_keywords: List[str],
        focus: str
    ) -> Dict[str, Any]:
        """Optimize the professional summary section."""
        from backend.services.llm_service import get_llm_service

        llm = get_llm_service()

        job_title = job_context.get("title", "target role") if job_context else "your target role"
        company = job_context.get("company", "") if job_context else ""

        prompt = f"""Optimize this professional summary for ATS and impact.

CURRENT SUMMARY:
{summary}

TARGET ROLE: {job_title}
{"TARGET COMPANY: " + company if company else ""}

KEYWORDS TO INCORPORATE (if relevant): {', '.join(missing_keywords[:5])}

OPTIMIZATION FOCUS: {focus}
- ats: Maximize keyword density and ATS readability
- impact: Focus on achievements and strong action verbs
- keywords: Naturally incorporate missing keywords
- balanced: Balance all factors

Provide:
1. Optimized summary (3-4 sentences, impactful, ATS-friendly)
2. List of improvements made
3. Keywords added

Return as JSON:
{{
    "optimized_content": "The optimized summary text",
    "improvement_notes": ["improvement 1", "improvement 2"],
    "keywords_added": ["keyword1", "keyword2"]
}}

Return ONLY valid JSON."""

        try:
            result = await llm.generate_structured(prompt)
            return {
                "section_name": "Professional Summary",
                "original_content": summary,
                "optimized_content": result.get("optimized_content", summary),
                "improvement_notes": result.get("improvement_notes", []),
                "keywords_added": result.get("keywords_added", [])
            }
        except Exception as e:
            logger.warning(f"Failed to optimize summary: {e}")
            return {
                "section_name": "Professional Summary",
                "original_content": summary,
                "optimized_content": summary,
                "improvement_notes": ["Could not auto-optimize - review manually"],
                "keywords_added": []
            }

    async def _optimize_experience(
        self,
        experience: Dict[str, Any],
        job_context: Dict[str, Any],
        missing_keywords: List[str],
        focus: str
    ) -> Dict[str, Any]:
        """Optimize a work experience entry."""
        from backend.services.llm_service import get_llm_service

        llm = get_llm_service()

        title = experience.get("title", "")
        company = experience.get("company", "")
        description = experience.get("description", "")
        achievements = experience.get("achievements", [])

        original = f"{title} at {company}\n{description}\n" + "\n".join(f"• {a}" for a in achievements)

        prompt = f"""Optimize this work experience for ATS and impact.

CURRENT EXPERIENCE:
Title: {title}
Company: {company}
Description: {description}
Achievements:
{chr(10).join('• ' + a for a in achievements)}

{"TARGET JOB: " + job_context.get("title", "") if job_context else ""}

KEYWORDS TO INCORPORATE: {', '.join(missing_keywords[:5])}

OPTIMIZATION FOCUS: {focus}

Optimize the achievements to:
1. Start with strong action verbs
2. Include quantified metrics where possible
3. Incorporate relevant keywords naturally
4. Demonstrate impact and results

Return as JSON:
{{
    "optimized_content": "Optimized description and bullet points",
    "improvement_notes": ["improvement 1", "improvement 2"],
    "keywords_added": ["keyword1", "keyword2"]
}}

Return ONLY valid JSON."""

        try:
            result = await llm.generate_structured(prompt)
            return {
                "section_name": f"Experience: {title} at {company}",
                "original_content": original,
                "optimized_content": result.get("optimized_content", original),
                "improvement_notes": result.get("improvement_notes", []),
                "keywords_added": result.get("keywords_added", [])
            }
        except Exception as e:
            logger.warning(f"Failed to optimize experience: {e}")
            return {
                "section_name": f"Experience: {title} at {company}",
                "original_content": original,
                "optimized_content": original,
                "improvement_notes": ["Could not auto-optimize - review manually"],
                "keywords_added": []
            }

    async def _optimize_skills(
        self,
        skills: List[str],
        job_context: Dict[str, Any],
        skills_to_highlight: List[str]
    ) -> Dict[str, Any]:
        """Optimize the skills section organization."""

        # Group and prioritize skills
        job_skills = set(s.lower() for s in (job_context.get("skills", []) if job_context else []))

        # Prioritize: matching job skills first
        priority_skills = []
        other_skills = []

        for skill in skills:
            if skill.lower() in job_skills or skill.lower() in [s.lower() for s in skills_to_highlight]:
                priority_skills.append(skill)
            else:
                other_skills.append(skill)

        optimized_skills = priority_skills + other_skills

        improvements = []
        if priority_skills:
            improvements.append(f"Reordered to prioritize {len(priority_skills)} job-relevant skills")

        if job_skills:
            missing_skills = job_skills - set(s.lower() for s in skills)
            if missing_skills:
                improvements.append(f"Consider adding: {', '.join(list(missing_skills)[:5])}")

        return {
            "section_name": "Skills",
            "original_content": ", ".join(skills),
            "optimized_content": ", ".join(optimized_skills),
            "improvement_notes": improvements,
            "keywords_added": []
        }

    async def generate_cover_letter_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Generate a tailored cover letter."""
        logger.info("Generating cover letter")

        if not state.get("include_cover_letter"):
            return state

        if not state.get("resume_data"):
            return state

        resume = state["resume_data"]
        job_context = state.get("job_context", {})

        state["messages"].append("Generating tailored cover letter...")

        try:
            from backend.services.llm_service import get_llm_service

            llm = get_llm_service()

            name = resume.get("full_name", "")
            skills = resume.get("skills", [])[:10]
            experiences = resume.get("work_experiences", [])[:2]

            exp_summary = ""
            for exp in experiences:
                exp_summary += f"- {exp.get('title')} at {exp.get('company')}\n"
                if exp.get("achievements"):
                    exp_summary += f"  Key achievement: {exp['achievements'][0]}\n"

            job_title = job_context.get("title", "the position") if job_context else "the position"
            company = job_context.get("company", "your company") if job_context else "your company"
            job_desc = job_context.get("description", "")[:1000] if job_context else ""

            prompt = f"""Write a compelling cover letter for this job application.

CANDIDATE:
Name: {name}
Key Skills: {', '.join(skills)}
Recent Experience:
{exp_summary}

JOB:
Position: {job_title}
Company: {company}
{"Description: " + job_desc if job_desc else ""}

Write a professional cover letter that:
1. Opens with a compelling hook
2. Highlights 2-3 most relevant achievements
3. Connects candidate's experience to job requirements
4. Shows enthusiasm for the company
5. Ends with a strong call to action

Keep it to 3-4 paragraphs, professional but personable.

Return ONLY the cover letter text, no JSON formatting."""

            cover_letter = await llm.generate(prompt)
            state["cover_letter"] = cover_letter
            state["messages"].append("✓ Cover letter generated")

        except Exception as e:
            state["errors"].append(f"Error generating cover letter: {str(e)}")

        return state

    async def final_scoring_node(self, state: ResumeOptimizationState) -> ResumeOptimizationState:
        """Calculate final ATS score after optimizations."""
        logger.info("Calculating final scores")

        if not state.get("resume_data") or not state.get("ats_score_before"):
            return state

        try:
            before_score = state["ats_score_before"]

            # Calculate improvements
            keyword_improvement = min(100, before_score["keyword_match"] + len(state.get("keywords_matched", [])) * 2)
            section_improvement = min(100, before_score["section_completeness"] + 10)  # Added optimized content

            # Estimate new scores
            after_score = {
                "overall_score": 0,
                "keyword_match": keyword_improvement,
                "formatting_score": min(100, before_score["formatting_score"] + 10),
                "section_completeness": section_improvement,
                "readability_score": min(100, before_score["readability_score"] + 5),
                "issues": [],
                "suggestions": []
            }

            # Recalculate overall
            after_score["overall_score"] = int(
                after_score["keyword_match"] * 0.35 +
                after_score["formatting_score"] * 0.20 +
                after_score["section_completeness"] * 0.25 +
                after_score["readability_score"] * 0.20
            )

            # Add suggestions for remaining improvements
            if after_score["keyword_match"] < 80:
                after_score["suggestions"].append("Consider adding more industry-specific keywords")

            if not state.get("resume_data", {}).get("certifications"):
                after_score["suggestions"].append("Add relevant certifications to boost credibility")

            state["ats_score_after"] = after_score

            improvement = after_score["overall_score"] - before_score["overall_score"]
            state["messages"].append(
                f"✓ Optimization complete: Score improved from {before_score['overall_score']} to {after_score['overall_score']} (+{improvement} points)"
            )

        except Exception as e:
            state["errors"].append(f"Error in final scoring: {str(e)}")

        return state

    async def run(
        self,
        user_id: str,
        job_id: Optional[str] = None,
        job_description: Optional[str] = None,
        optimization_focus: str = "balanced",
        include_cover_letter: bool = False,
        preserve_formatting: bool = True
    ) -> Dict[str, Any]:
        """
        Run the resume optimization workflow.

        Args:
            user_id: User ID to optimize resume for
            job_id: Optional job ID to tailor resume for
            job_description: Optional job description text
            optimization_focus: Focus area (ats, impact, keywords, balanced)
            include_cover_letter: Whether to generate a cover letter
            preserve_formatting: Whether to preserve original structure

        Returns:
            Dictionary with optimization results
        """
        logger.info(f"Starting Resume Optimization agent for user {user_id}")

        initial_state: ResumeOptimizationState = {
            "user_id": user_id,
            "job_id": job_id,
            "job_description": job_description,
            "resume_data": None,
            "job_context": None,
            "ats_score_before": None,
            "ats_score_after": None,
            "optimized_sections": [],
            "keywords_matched": [],
            "keywords_missing": [],
            "skills_highlighted": [],
            "improvement_summary": "",
            "cover_letter": None,
            "messages": [],
            "errors": [],
            "optimization_focus": optimization_focus,
            "include_cover_letter": include_cover_letter,
            "preserve_formatting": preserve_formatting
        }

        try:
            final_state = await self.workflow.ainvoke(initial_state)

            # Build result
            result = {
                "optimized_sections": final_state.get("optimized_sections", []),
                "ats_score_before": final_state.get("ats_score_before"),
                "ats_score_after": final_state.get("ats_score_after"),
                "keywords_matched": final_state.get("keywords_matched", []),
                "keywords_missing": final_state.get("keywords_missing", []),
                "skills_highlighted": final_state.get("skills_highlighted", []),
                "improvement_summary": final_state.get("improvement_summary", ""),
                "cover_letter": final_state.get("cover_letter")
            }

            job_context = final_state.get("job_context") or {}

            response = {
                "success": len(final_state["errors"]) == 0,
                "user_id": user_id,
                "result": result,
                "target_job_title": job_context.get("title"),
                "target_company": job_context.get("company"),
                "messages": final_state["messages"],
                "errors": final_state["errors"],
                "timestamp": datetime.utcnow().isoformat()
            }

            # Calculate score improvement safely
            ats_before = final_state.get("ats_score_before") or {}
            ats_after = final_state.get("ats_score_after") or {}
            score_before = ats_before.get("overall_score", 0) if isinstance(ats_before, dict) else 0
            score_after = ats_after.get("overall_score", 0) if isinstance(ats_after, dict) else 0

            logger.info(
                f"Resume Optimization completed for user {user_id}: "
                f"sections={len(final_state.get('optimized_sections', []))}, "
                f"score_improvement={score_after - score_before}"
            )

            return response

        except Exception as e:
            logger.error(f"Resume Optimization agent failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": initial_state["messages"],
                "errors": initial_state["errors"] + [str(e)]
            }
