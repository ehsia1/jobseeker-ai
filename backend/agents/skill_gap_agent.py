"""Skill Gap & Career Development Agent.

This agent provides comprehensive skill gap analysis and learning recommendations:
1. Analyze user's current skills from resume and profile
2. Compare against target job requirements
3. Identify skill gaps with priority levels
4. Recommend learning resources (courses, certifications, projects)
5. Create personalized learning roadmap with timelines
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from backend.services.llm_service import get_llm_service


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling various formats."""
    if not text:
        logger.warning("extract_json received empty text")
        return {}

    content = text.strip()
    original_content = content

    # Try to extract JSON from code blocks
    if "```" in content:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            content = json_match.group(1).strip()

    # Try to find JSON object in the text
    if not content.startswith('{'):
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)

    # Clean up common LLM output issues
    content = re.sub(r',(\s*[}\]])', r'\1', content)

    # Fix control characters inside string values
    def escape_control_chars(match):
        s = match.group(0)
        s = s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return s

    content = re.sub(r'"(?:[^"\\]|\\.)*"', escape_control_chars, content)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Content being parsed (first 500 chars): {content[:500]}")
        raise


from backend.database import async_session
from backend.models.user import User, UserProfile
from backend.models.resume import Resume

from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class SkillGapAgentState(TypedDict, total=False):
    """State for the Skill Gap Agent."""
    # Input
    user_id: str
    target_job_title: str
    target_job_description: Optional[str]
    target_industry: Optional[str]
    target_company: Optional[str]
    timeframe_months: int  # How long user has to learn
    learning_hours_per_week: int
    include_certifications: bool
    include_projects: bool
    focus_area: str  # technical, soft_skills, both

    # Profile data
    current_skills: List[str]
    current_skill_levels: Dict[str, str]  # skill -> level (beginner/intermediate/advanced)
    education: List[Dict[str, Any]]
    work_experience: List[Dict[str, Any]]
    current_role: str
    years_experience: int

    # Analysis results
    required_skills: List[Dict[str, Any]]  # {skill, importance, category}
    skill_gaps: List[Dict[str, Any]]  # {skill, gap_level, priority, category}
    transferable_skills: List[str]  # Skills user has that are relevant
    skill_overlap_percent: float

    # Recommendations
    learning_resources: List[Dict[str, Any]]  # {name, type, url, duration, cost, provider}
    recommended_certifications: List[Dict[str, Any]]
    recommended_projects: List[Dict[str, Any]]
    learning_roadmap: Dict[str, Any]  # Phased plan with milestones

    # Market context
    market_demand: Dict[str, str]  # skill -> demand level
    salary_impact: Dict[str, float]  # skill -> estimated salary boost %

    # Output
    messages: List[str]
    errors: List[str]


# In-memory storage for run results
_skill_gap_runs: Dict[str, Dict[str, Any]] = {}


def get_skill_gap_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a skill gap analysis run by ID."""
    return _skill_gap_runs.get(run_id)


def update_skill_gap_run(run_id: str, updates: Dict[str, Any]) -> None:
    """Update a skill gap analysis run."""
    if run_id in _skill_gap_runs:
        _skill_gap_runs[run_id].update(updates)


class SkillGapAgent:
    """Agent for skill gap analysis and learning path recommendations."""

    def __init__(self):
        self.llm_service = None
        self.graph = None

    async def initialize(self) -> None:
        """Initialize the agent with LLM and graph."""
        self.llm_service = get_llm_service()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(SkillGapAgentState)

        # Add nodes
        workflow.add_node("load_user_data", self._load_user_data_node)
        workflow.add_node("analyze_target_requirements", self._analyze_target_requirements_node)
        workflow.add_node("identify_skill_gaps", self._identify_skill_gaps_node)
        workflow.add_node("research_market_demand", self._research_market_demand_node)
        workflow.add_node("recommend_resources", self._recommend_resources_node)
        workflow.add_node("build_roadmap", self._build_roadmap_node)
        workflow.add_node("finalize", self._finalize_node)

        # Set entry point
        workflow.set_entry_point("load_user_data")

        # Add edges
        workflow.add_edge("load_user_data", "analyze_target_requirements")
        workflow.add_edge("analyze_target_requirements", "identify_skill_gaps")
        workflow.add_edge("identify_skill_gaps", "research_market_demand")
        workflow.add_edge("research_market_demand", "recommend_resources")
        workflow.add_edge("recommend_resources", "build_roadmap")
        workflow.add_edge("build_roadmap", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _load_user_data_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Load user profile and resume data."""
        messages = state.get("messages", [])
        messages.append("Loading your profile and skills...")

        user_id = state.get("user_id")
        current_skills = []
        current_skill_levels = {}
        education = []
        work_experience = []
        current_role = ""
        years_experience = 0

        if user_id:
            try:
                async with async_session() as session:
                    result = await session.execute(
                        select(User)
                        .options(
                            selectinload(User.profile),
                            selectinload(User.resume)
                        )
                        .where(User.id == uuid.UUID(user_id))
                    )
                    user = result.scalar_one_or_none()

                    if user and user.profile:
                        profile = user.profile
                        current_role = profile.job_title or ""
                        years_experience = profile.experience_years or 0
                        if profile.skills:
                            current_skills.extend(profile.skills)
                            # Default skill levels to intermediate
                            for skill in profile.skills:
                                current_skill_levels[skill] = "intermediate"

                    if user and user.resume:
                        resume = user.resume
                        if resume.skills:
                            for skill in resume.skills:
                                if skill not in current_skills:
                                    current_skills.append(skill)
                                    current_skill_levels[skill] = "intermediate"

                        if resume.education:
                            education = resume.education

                        # Load work experiences
                        if hasattr(resume, 'work_experiences'):
                            result = await session.execute(
                                select(Resume)
                                .options(selectinload(Resume.work_experiences))
                                .where(Resume.id == resume.id)
                            )
                            resume_with_exp = result.scalar_one_or_none()
                            if resume_with_exp and resume_with_exp.work_experiences:
                                for exp in resume_with_exp.work_experiences:
                                    work_experience.append({
                                        "title": exp.title,
                                        "company": exp.company,
                                        "description": exp.description,
                                        "start_date": str(exp.start_date) if exp.start_date else None,
                                        "end_date": str(exp.end_date) if exp.end_date else None,
                                    })

            except Exception as e:
                logger.error(f"Error loading user data: {e}")
                messages.append(f"Note: Could not load all profile data")

        return {
            "messages": messages,
            "current_skills": current_skills,
            "current_skill_levels": current_skill_levels,
            "education": education,
            "work_experience": work_experience,
            "current_role": current_role,
            "years_experience": years_experience,
        }

    async def _analyze_target_requirements_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Analyze the target job requirements."""
        messages = state.get("messages", [])
        messages.append("Analyzing target job requirements...")

        target_job_title = state.get("target_job_title", "")
        target_job_description = state.get("target_job_description", "")
        target_industry = state.get("target_industry", "technology")
        focus_area = state.get("focus_area", "both")

        prompt = f"""Analyze the requirements for this target job and identify all skills needed.

Target Job Title: {target_job_title}
Industry: {target_industry}
Focus Area: {focus_area}

{f"Job Description: {target_job_description}" if target_job_description else ""}

Return a JSON object with the required skills categorized by importance and type:

{{
    "required_skills": [
        {{
            "skill": "skill name",
            "importance": "critical|important|nice_to_have",
            "category": "technical|soft_skill|domain_knowledge|tool",
            "description": "brief description of how this skill is used"
        }}
    ],
    "typical_experience_level": "entry|mid|senior|lead",
    "key_technologies": ["list of main technologies/tools"],
    "certifications_valued": ["list of relevant certifications"],
    "common_projects": ["types of projects typically worked on"]
}}

Include 15-25 skills covering both technical and soft skills.
Be specific - instead of "programming", list specific languages.
Return ONLY valid JSON, no additional text."""

        try:
            response = await self.llm_service.generate(prompt)
            result = extract_json(response)
            required_skills = result.get("required_skills", [])

            return {
                "messages": messages,
                "required_skills": required_skills,
            }

        except Exception as e:
            logger.error(f"Error analyzing target requirements: {e}")
            messages.append(f"Warning: Limited requirements analysis available")
            return {
                "messages": messages,
                "required_skills": [],
            }

    async def _identify_skill_gaps_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Identify gaps between current skills and requirements."""
        messages = state.get("messages", [])
        messages.append("Identifying skill gaps...")

        current_skills = state.get("current_skills", [])
        current_skill_levels = state.get("current_skill_levels", {})
        required_skills = state.get("required_skills", [])
        target_job_title = state.get("target_job_title", "")

        prompt = f"""Compare the user's current skills with the required skills for {target_job_title}.

Current Skills: {json.dumps(current_skills)}
Current Skill Levels: {json.dumps(current_skill_levels)}

Required Skills:
{json.dumps(required_skills, indent=2)}

Analyze the gap and return a JSON object:

{{
    "skill_gaps": [
        {{
            "skill": "skill name",
            "gap_level": "not_present|needs_improvement|minor_gap",
            "priority": "high|medium|low",
            "category": "technical|soft_skill|domain_knowledge|tool",
            "learning_effort": "weeks|months|long_term",
            "prerequisite_skills": ["list of skills needed first"]
        }}
    ],
    "transferable_skills": ["skills user has that apply to the new role"],
    "skill_overlap_percent": 45,
    "strongest_areas": ["areas where user is already strong"],
    "critical_gaps": ["most important skills to acquire first"]
}}

Prioritize gaps by:
1. Critical skills that are completely missing
2. Important skills that need improvement
3. Nice-to-have skills

Return ONLY valid JSON, no additional text."""

        try:
            response = await self.llm_service.generate(prompt)
            result = extract_json(response)

            skill_gaps = result.get("skill_gaps", [])
            transferable_skills = result.get("transferable_skills", [])
            skill_overlap_percent = safe_float(result.get("skill_overlap_percent", 0))

            # Sort gaps by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            skill_gaps.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

            messages.append(f"Found {len(skill_gaps)} skill gaps to address")

            return {
                "messages": messages,
                "skill_gaps": skill_gaps,
                "transferable_skills": transferable_skills,
                "skill_overlap_percent": skill_overlap_percent,
            }

        except Exception as e:
            logger.error(f"Error identifying skill gaps: {e}")
            messages.append(f"Warning: Limited gap analysis available")
            return {
                "messages": messages,
                "skill_gaps": [],
                "transferable_skills": [],
                "skill_overlap_percent": 0,
            }

    async def _research_market_demand_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Research market demand for skills and salary impact."""
        messages = state.get("messages", [])
        messages.append("Researching market demand...")

        skill_gaps = state.get("skill_gaps", [])
        target_job_title = state.get("target_job_title", "")
        target_industry = state.get("target_industry", "technology")

        skills_to_research = [gap.get("skill", "") for gap in skill_gaps[:15]]

        prompt = f"""Analyze market demand for these skills in the context of {target_job_title} roles in {target_industry}:

Skills: {json.dumps(skills_to_research)}

Return a JSON object with market insights:

{{
    "market_demand": {{
        "skill_name": "very_high|high|moderate|low"
    }},
    "salary_impact": {{
        "skill_name": 5.0
    }},
    "trending_skills": ["skills with growing demand"],
    "declining_skills": ["skills becoming less important"],
    "emerging_technologies": ["new skills to watch"],
    "industry_insights": "Brief paragraph about skill trends in this industry"
}}

The salary_impact should be estimated percentage increase for having that skill.
Return ONLY valid JSON, no additional text."""

        try:
            response = await self.llm_service.generate(prompt)
            result = extract_json(response)

            market_demand = result.get("market_demand", {})
            salary_impact = {}
            for skill, impact in result.get("salary_impact", {}).items():
                salary_impact[skill] = safe_float(impact)

            return {
                "messages": messages,
                "market_demand": market_demand,
                "salary_impact": salary_impact,
            }

        except Exception as e:
            logger.error(f"Error researching market demand: {e}")
            return {
                "messages": messages,
                "market_demand": {},
                "salary_impact": {},
            }

    async def _recommend_resources_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Recommend learning resources for each skill gap."""
        messages = state.get("messages", [])
        messages.append("Finding learning resources...")

        skill_gaps = state.get("skill_gaps", [])
        include_certifications = state.get("include_certifications", True)
        include_projects = state.get("include_projects", True)
        learning_hours_per_week = state.get("learning_hours_per_week", 10)

        # Focus on high and medium priority gaps
        priority_gaps = [g for g in skill_gaps if g.get("priority") in ["high", "medium"]][:10]

        prompt = f"""Recommend learning resources for these skill gaps:

Skill Gaps to Address:
{json.dumps(priority_gaps, indent=2)}

User's Available Learning Time: {learning_hours_per_week} hours per week
Include Certifications: {include_certifications}
Include Projects: {include_projects}

Return a JSON object with recommendations:

{{
    "learning_resources": [
        {{
            "skill": "skill name this resource teaches",
            "name": "Course/Resource Name",
            "type": "online_course|book|tutorial|bootcamp|video_series|documentation",
            "provider": "Coursera|Udemy|Pluralsight|LinkedIn Learning|YouTube|Official Docs|etc",
            "url": "example URL or search query",
            "duration_hours": 20,
            "cost": "free|$|$$|$$$",
            "difficulty": "beginner|intermediate|advanced",
            "rating": 4.5,
            "key_topics": ["topic1", "topic2"]
        }}
    ],
    "recommended_certifications": [
        {{
            "name": "Certification Name",
            "provider": "AWS|Google|Microsoft|etc",
            "skill": "main skill validated",
            "cost_range": "$200-$400",
            "prep_time_months": 2,
            "career_value": "high|medium|low",
            "prerequisites": ["required skills/certs"]
        }}
    ],
    "recommended_projects": [
        {{
            "title": "Project Title",
            "description": "What to build",
            "skills_practiced": ["skill1", "skill2"],
            "difficulty": "beginner|intermediate|advanced",
            "estimated_hours": 40,
            "portfolio_value": "high|medium|low"
        }}
    ]
}}

Prioritize:
- Well-reviewed, popular resources
- Hands-on, practical learning
- Resources that cover multiple skills efficiently
- Mix of free and paid options

Return ONLY valid JSON, no additional text."""

        try:
            response = await self.llm_service.generate(prompt)
            result = extract_json(response)

            learning_resources = result.get("learning_resources", [])
            recommended_certifications = result.get("recommended_certifications", []) if include_certifications else []
            recommended_projects = result.get("recommended_projects", []) if include_projects else []

            return {
                "messages": messages,
                "learning_resources": learning_resources,
                "recommended_certifications": recommended_certifications,
                "recommended_projects": recommended_projects,
            }

        except Exception as e:
            logger.error(f"Error recommending resources: {e}")
            return {
                "messages": messages,
                "learning_resources": [],
                "recommended_certifications": [],
                "recommended_projects": [],
            }

    async def _build_roadmap_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Build a personalized learning roadmap."""
        messages = state.get("messages", [])
        messages.append("Building your learning roadmap...")

        skill_gaps = state.get("skill_gaps", [])
        learning_resources = state.get("learning_resources", [])
        recommended_certifications = state.get("recommended_certifications", [])
        recommended_projects = state.get("recommended_projects", [])
        timeframe_months = state.get("timeframe_months", 6)
        learning_hours_per_week = state.get("learning_hours_per_week", 10)
        target_job_title = state.get("target_job_title", "")

        prompt = f"""Create a personalized learning roadmap for transitioning to {target_job_title}.

Timeframe: {timeframe_months} months
Available Time: {learning_hours_per_week} hours per week
Total Available Hours: {timeframe_months * 4 * learning_hours_per_week}

Skill Gaps (prioritized):
{json.dumps(skill_gaps[:10], indent=2)}

Available Resources:
{json.dumps(learning_resources[:8], indent=2)}

Certifications to Consider:
{json.dumps(recommended_certifications[:3], indent=2)}

Projects to Build:
{json.dumps(recommended_projects[:3], indent=2)}

Return a JSON object with a phased learning plan:

{{
    "roadmap": {{
        "total_duration_months": {timeframe_months},
        "phases": [
            {{
                "phase_number": 1,
                "name": "Foundation Phase",
                "duration_weeks": 4,
                "focus_skills": ["skill1", "skill2"],
                "activities": [
                    {{
                        "type": "course|project|certification_prep|practice",
                        "name": "Activity name",
                        "hours_per_week": 5,
                        "description": "What you'll learn"
                    }}
                ],
                "milestones": ["Complete X course", "Build Y project"],
                "success_metrics": ["Can do X", "Understand Y"]
            }}
        ],
        "weekly_schedule_template": {{
            "monday": "Focus area",
            "tuesday": "Focus area",
            "wednesday": "Focus area",
            "thursday": "Focus area",
            "friday": "Focus area",
            "weekend": "Projects/practice"
        }},
        "key_milestones": [
            {{
                "month": 1,
                "milestone": "Description",
                "skills_acquired": ["skill1"]
            }}
        ],
        "job_ready_indicators": [
            "Can confidently discuss X in interviews",
            "Portfolio includes Y projects",
            "Certified in Z"
        ]
    }},
    "quick_wins": ["Skills you can acquire in under 2 weeks"],
    "long_term_investments": ["Skills that take time but have high ROI"],
    "parallel_paths": ["Skills you can learn simultaneously"]
}}

Make the plan realistic and achievable. Include buffer time for review and practice.
Return ONLY valid JSON, no additional text."""

        try:
            response = await self.llm_service.generate(prompt)
            result = extract_json(response)

            learning_roadmap = result.get("roadmap", {})

            return {
                "messages": messages,
                "learning_roadmap": learning_roadmap,
            }

        except Exception as e:
            logger.error(f"Error building roadmap: {e}")
            return {
                "messages": messages,
                "learning_roadmap": {},
            }

    async def _finalize_node(self, state: SkillGapAgentState) -> Dict[str, Any]:
        """Finalize the analysis and prepare output."""
        messages = state.get("messages", [])
        skill_gaps = state.get("skill_gaps", [])
        skill_overlap_percent = state.get("skill_overlap_percent", 0)

        high_priority_gaps = len([g for g in skill_gaps if g.get("priority") == "high"])
        total_gaps = len(skill_gaps)

        summary = f"Analysis complete! You have {skill_overlap_percent:.0f}% skill overlap. "
        summary += f"Found {total_gaps} skill gaps ({high_priority_gaps} high priority)."
        messages.append(summary)

        return {
            "messages": messages,
            "status": "completed",
        }

    async def run(
        self,
        run_id: str,
        user_id: str,
        target_job_title: str,
        target_job_description: Optional[str] = None,
        target_industry: Optional[str] = "technology",
        target_company: Optional[str] = None,
        timeframe_months: int = 6,
        learning_hours_per_week: int = 10,
        include_certifications: bool = True,
        include_projects: bool = True,
        focus_area: str = "both",
    ) -> Dict[str, Any]:
        """Run the skill gap analysis agent."""
        logger.info(f"Starting Skill Gap Analysis run {run_id}")

        # Initialize run storage
        _skill_gap_runs[run_id] = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }

        try:
            if not self.graph:
                await self.initialize()

            initial_state: SkillGapAgentState = {
                "user_id": user_id,
                "target_job_title": target_job_title,
                "target_job_description": target_job_description,
                "target_industry": target_industry,
                "target_company": target_company,
                "timeframe_months": timeframe_months,
                "learning_hours_per_week": learning_hours_per_week,
                "include_certifications": include_certifications,
                "include_projects": include_projects,
                "focus_area": focus_area,
                "messages": [],
                "errors": [],
            }

            result = await self.graph.ainvoke(initial_state)

            output = {
                "status": "completed",
                "target_job_title": target_job_title,
                "target_industry": target_industry,
                "current_skills": result.get("current_skills", []),
                "skill_gaps": result.get("skill_gaps", []),
                "transferable_skills": result.get("transferable_skills", []),
                "skill_overlap_percent": result.get("skill_overlap_percent", 0),
                "market_demand": result.get("market_demand", {}),
                "salary_impact": result.get("salary_impact", {}),
                "learning_resources": result.get("learning_resources", []),
                "recommended_certifications": result.get("recommended_certifications", []),
                "recommended_projects": result.get("recommended_projects", []),
                "learning_roadmap": result.get("learning_roadmap", {}),
                "messages": result.get("messages", []),
                "errors": result.get("errors", []),
            }

            _skill_gap_runs[run_id].update(output)
            logger.info(f"Skill Gap Analysis run {run_id} completed successfully")
            return output

        except Exception as e:
            logger.error(f"Skill Gap Analysis run {run_id} failed: {e}")
            error_output = {
                "status": "failed",
                "error": str(e),
                "errors": [str(e)],
                "messages": ["Analysis failed"],
            }
            _skill_gap_runs[run_id].update(error_output)
            return error_output


# Singleton instance
_agent_instance: Optional[SkillGapAgent] = None


async def get_skill_gap_agent() -> SkillGapAgent:
    """Get or create the skill gap agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SkillGapAgent()
        await _agent_instance.initialize()
    return _agent_instance
