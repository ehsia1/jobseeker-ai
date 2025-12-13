"""Interview Prep Agent - AI-powered interview preparation and coaching."""

import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from uuid import UUID

from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.models.job import Job
from backend.models.user import UserProfile
from backend.models.interview import InterviewType, DifficultyLevel

logger = logging.getLogger(__name__)


class InterviewPrepState(TypedDict):
    """State for the interview prep agent."""
    user_id: str
    job_id: Optional[str]
    user_profile: Optional[Dict[str, Any]]
    job_context: Optional[Dict[str, Any]]
    interview_plan: Optional[Dict[str, Any]]
    session_id: Optional[str]
    questions_generated: int
    prep_tips: List[str]
    focus_areas: List[str]
    skill_gaps: List[str]
    messages: List[str]
    errors: List[str]
    # Config
    interview_type: str
    difficulty: str
    num_questions: int


class InterviewPrepAgent:
    """Agent for personalized interview preparation."""

    def __init__(self, db: AsyncSession):
        """Initialize the Interview Prep agent."""
        self.db = db
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
            responses=["I'll help you prepare for your interview."]
        )

    def _build_workflow(self):
        """Build the LangGraph workflow for interview prep."""
        workflow = StateGraph(InterviewPrepState)

        # Add nodes
        workflow.add_node("analyze_profile", self.analyze_profile_node)
        workflow.add_node("analyze_job", self.analyze_job_node)
        workflow.add_node("identify_gaps", self.identify_gaps_node)
        workflow.add_node("create_prep_plan", self.create_prep_plan_node)
        workflow.add_node("create_session", self.create_session_node)
        workflow.add_node("generate_tips", self.generate_tips_node)

        # Define edges
        workflow.set_entry_point("analyze_profile")
        workflow.add_edge("analyze_profile", "analyze_job")
        workflow.add_edge("analyze_job", "identify_gaps")
        workflow.add_edge("identify_gaps", "create_prep_plan")
        workflow.add_edge("create_prep_plan", "create_session")
        workflow.add_edge("create_session", "generate_tips")
        workflow.add_edge("generate_tips", END)

        return workflow.compile()

    async def analyze_profile_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """Analyze user profile for interview context."""
        logger.info(f"Analyzing profile for user {state['user_id']}")
        state["messages"].append("Analyzing your profile...")

        try:
            result = await self.db.execute(
                select(UserProfile).where(UserProfile.user_id == state["user_id"])
            )
            profile = result.scalar_one_or_none()

            if profile:
                state["user_profile"] = {
                    "profession": profile.profession,
                    "job_title": profile.job_title,
                    "skills": profile.skills or [],
                    "experience_years": profile.experience_years or 0,
                    "certifications": profile.certifications or [],
                    "location": profile.location
                }
                state["messages"].append(
                    f"✓ Profile loaded: {profile.job_title or profile.profession or 'Professional'} "
                    f"with {profile.experience_years or 0} years experience"
                )
            else:
                state["user_profile"] = {
                    "skills": [],
                    "experience_years": 0
                }
                state["messages"].append("⚠ No profile found, using default settings")

        except Exception as e:
            state["errors"].append(f"Error loading profile: {str(e)}")

        return state

    async def analyze_job_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """Analyze job requirements if job_id provided."""
        logger.info("Analyzing job requirements")

        if not state.get("job_id"):
            state["messages"].append("No specific job provided - using general interview prep")
            state["job_context"] = None
            return state

        try:
            # Parse job_id - could be composite (source_sourceId) or UUID
            job = None
            job_id = state["job_id"]

            if "_" in job_id:
                parts = job_id.split("_", 1)
                source = parts[0]
                source_id = parts[1] if len(parts) > 1 else None
                result = await self.db.execute(
                    select(Job).where(Job.source == source, Job.source_id == source_id)
                )
                job = result.scalar_one_or_none()

            if not job:
                try:
                    result = await self.db.execute(
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
                    "description": job.description[:2000] if job.description else "",
                    "skills": job.skills or [],
                    "requirements": job.requirements or [],
                    "remote": job.remote
                }
                state["messages"].append(
                    f"✓ Job analyzed: {job.title} at {job.company}"
                )
            else:
                state["messages"].append("⚠ Job not found, using general interview prep")

        except Exception as e:
            state["errors"].append(f"Error analyzing job: {str(e)}")

        return state

    async def identify_gaps_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """Identify skill gaps between user profile and job requirements."""
        logger.info("Identifying skill gaps")

        user_skills = set(
            s.lower() for s in (state.get("user_profile", {}).get("skills") or [])
        )

        if state.get("job_context"):
            job_skills = set(
                s.lower() for s in (state["job_context"].get("skills") or [])
            )

            # Find skills user is missing
            gaps = list(job_skills - user_skills)
            matches = list(user_skills & job_skills)

            state["skill_gaps"] = gaps[:10]
            state["focus_areas"] = matches[:5] + gaps[:5]  # Focus on both strengths and gaps

            if gaps:
                state["messages"].append(
                    f"✓ Identified {len(gaps)} skill gaps to address"
                )
            else:
                state["messages"].append("✓ Strong skill match - focus on demonstrating experience")
        else:
            # General interview prep - focus on user's top skills
            state["skill_gaps"] = []
            state["focus_areas"] = list(user_skills)[:10]
            state["messages"].append("✓ Focus areas set from your skill profile")

        return state

    async def create_prep_plan_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """Create a personalized interview prep plan."""
        logger.info("Creating interview prep plan")

        try:
            interview_type = state.get("interview_type", "behavioral")
            difficulty = state.get("difficulty", "mid")

            # Determine interview type based on job
            if state.get("job_context"):
                job_title = state["job_context"].get("title", "").lower()
                job_desc = state["job_context"].get("description", "").lower()

                # Auto-detect interview type if not specified
                if interview_type == "auto":
                    if any(kw in job_title for kw in ["engineer", "developer", "architect"]):
                        if "senior" in job_title or "lead" in job_title:
                            interview_type = "system_design"
                            difficulty = "senior"
                        else:
                            interview_type = "technical"
                    elif any(kw in job_title for kw in ["manager", "director", "vp", "head"]):
                        interview_type = "behavioral"
                        difficulty = "lead"
                    elif any(kw in job_desc for kw in ["case study", "consulting"]):
                        interview_type = "case_study"
                    else:
                        interview_type = "behavioral"

            # Build the prep plan
            job_context = state.get("job_context") or {}
            state["interview_plan"] = {
                "interview_type": interview_type,
                "difficulty": difficulty,
                "focus_areas": state.get("focus_areas") or [],
                "skill_gaps_to_address": (state.get("skill_gaps") or [])[:3],
                "target_role": job_context.get("title"),
                "target_company": job_context.get("company"),
                "recommended_frameworks": self._get_frameworks(interview_type),
                "question_types": self._get_question_types(interview_type)
            }

            state["messages"].append(
                f"✓ Prep plan created: {interview_type.title()} interview at {difficulty} level"
            )

        except Exception as e:
            state["errors"].append(f"Error creating prep plan: {str(e)}")

        return state

    async def create_session_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """Create an interview practice session."""
        logger.info("Creating interview session")

        try:
            from backend.services.interview_service import InterviewCoachingService

            # Map string types to enums
            interview_type_map = {
                "behavioral": InterviewType.BEHAVIORAL,
                "technical": InterviewType.TECHNICAL,
                "system_design": InterviewType.SYSTEM_DESIGN,
                "case_study": InterviewType.CASE_STUDY,
                "situational": InterviewType.SITUATIONAL,
                "competency": InterviewType.COMPETENCY
            }

            difficulty_map = {
                "entry": DifficultyLevel.ENTRY,
                "mid": DifficultyLevel.MID,
                "senior": DifficultyLevel.SENIOR,
                "lead": DifficultyLevel.LEAD,
                "executive": DifficultyLevel.EXECUTIVE
            }

            plan = state.get("interview_plan") or {}
            interview_type = interview_type_map.get(
                plan.get("interview_type", "behavioral"),
                InterviewType.BEHAVIORAL
            )
            difficulty = difficulty_map.get(
                plan.get("difficulty", "mid"),
                DifficultyLevel.MID
            )

            # Get job context safely
            job_context = state.get("job_context") or {}
            job_id_str = job_context.get("id")
            job_id = UUID(job_id_str) if job_id_str else None

            # Create the session
            service = InterviewCoachingService(self.db)
            session = await service.create_session(
                user_id=UUID(state["user_id"]),
                interview_type=interview_type,
                difficulty=difficulty,
                job_id=job_id,
                target_role=plan.get("target_role"),
                target_company=plan.get("target_company"),
                focus_areas=plan.get("focus_areas") or [],
                total_questions=state.get("num_questions", 5)
            )

            # Generate all remaining questions upfront for the prep session
            job_context = state.get("job_context")
            additional_questions = await service.generate_all_session_questions(
                session=session,
                job_context=job_context
            )

            total_questions = 1 + additional_questions  # 1 from create_session + additional
            state["session_id"] = str(session.id)
            state["questions_generated"] = total_questions

            state["messages"].append(
                f"✓ Interview session created with {total_questions} questions"
            )

            await self.db.commit()

        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            state["errors"].append(f"Error creating session: {str(e)}")

        return state

    async def generate_tips_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """Generate personalized interview prep tips."""
        logger.info("Generating prep tips")

        try:
            tips = []
            plan = state.get("interview_plan") or {}
            interview_type = plan.get("interview_type", "behavioral")

            # General tips based on interview type
            if interview_type == "behavioral":
                tips.extend([
                    "Use the STAR method: Situation, Task, Action, Result for every answer",
                    "Prepare 5-7 stories that can be adapted to different questions",
                    "Quantify your achievements with specific numbers and metrics",
                    "Practice speaking your answers out loud, not just in your head"
                ])
            elif interview_type == "technical":
                tips.extend([
                    "Think aloud while solving problems - interviewers want to see your process",
                    "Ask clarifying questions before diving into a solution",
                    "Start with a brute force approach, then optimize",
                    "Test your code with edge cases before declaring it done"
                ])
            elif interview_type == "system_design":
                tips.extend([
                    "Start with requirements clarification - ask about scale, users, constraints",
                    "Draw high-level architecture before diving into details",
                    "Discuss trade-offs explicitly - there's no perfect design",
                    "Consider scalability, reliability, and maintainability"
                ])
            elif interview_type == "case_study":
                tips.extend([
                    "Structure your approach before answering",
                    "Ask clarifying questions to understand the problem fully",
                    "Use frameworks like MECE to organize your analysis",
                    "Summarize your recommendation clearly at the end"
                ])

            # Tips based on skill gaps
            if state.get("skill_gaps"):
                gaps = state["skill_gaps"][:3]
                tips.append(
                    f"Be prepared to discuss learning: {', '.join(gaps)} - "
                    "show enthusiasm for developing these skills"
                )

            # Tips based on job context
            job_context = state.get("job_context") or {}
            if job_context:
                company = job_context.get("company")
                if company:
                    tips.append(f"Research {company}'s culture, recent news, and mission statement")

            # Tips based on experience level
            user_profile = state.get("user_profile") or {}
            exp_years = user_profile.get("experience_years", 0) or 0
            if exp_years < 3:
                tips.append("Focus on demonstrating potential and eagerness to learn")
            elif exp_years >= 10:
                tips.append("Prepare examples that show leadership and strategic impact")

            state["prep_tips"] = tips
            state["messages"].append(f"✓ Generated {len(tips)} personalized prep tips")

        except Exception as e:
            state["errors"].append(f"Error generating tips: {str(e)}")

        return state

    def _get_frameworks(self, interview_type: str) -> List[str]:
        """Get recommended frameworks for interview type."""
        frameworks = {
            "behavioral": ["STAR (Situation, Task, Action, Result)", "CAR (Context, Action, Result)"],
            "technical": ["Problem-Approach-Solution", "UMPIRE (Understand, Match, Plan, Implement, Review, Evaluate)"],
            "system_design": ["Requirements-Architecture-Deep Dive-Tradeoffs", "RESHADED"],
            "case_study": ["Issue Tree", "MECE Framework", "Hypothesis-Driven"],
            "situational": ["STAR Method", "What-Why-How"],
            "competency": ["CAR Method", "SOAR (Situation, Obstacle, Action, Result)"]
        }
        return frameworks.get(interview_type, frameworks["behavioral"])

    def _get_question_types(self, interview_type: str) -> List[str]:
        """Get expected question types for interview."""
        types = {
            "behavioral": ["Leadership", "Teamwork", "Conflict Resolution", "Problem Solving", "Failure/Learning"],
            "technical": ["Coding", "Algorithms", "Data Structures", "System Design Basics", "Debugging"],
            "system_design": ["Scalability", "Database Design", "API Design", "Caching", "Load Balancing"],
            "case_study": ["Market Sizing", "Profitability", "Market Entry", "Mergers & Acquisitions"],
            "situational": ["Hypothetical Scenarios", "Decision Making", "Prioritization"],
            "competency": ["Core Competencies", "Role-Specific Skills", "Cultural Fit"]
        }
        return types.get(interview_type, types["behavioral"])

    async def run(
        self,
        user_id: str,
        job_id: Optional[str] = None,
        interview_type: str = "auto",
        difficulty: str = "mid",
        num_questions: int = 5
    ) -> Dict[str, Any]:
        """
        Run the interview prep workflow.

        Args:
            user_id: User ID to prepare for
            job_id: Optional job ID to tailor preparation
            interview_type: Type of interview (behavioral, technical, system_design, case_study, auto)
            difficulty: Difficulty level (entry, mid, senior, lead, executive)
            num_questions: Number of practice questions to generate

        Returns:
            Dictionary with prep plan and session details
        """
        logger.info(f"Starting Interview Prep agent for user {user_id}")

        initial_state: InterviewPrepState = {
            "user_id": user_id,
            "job_id": job_id,
            "user_profile": None,
            "job_context": None,
            "interview_plan": None,
            "session_id": None,
            "questions_generated": 0,
            "prep_tips": [],
            "focus_areas": [],
            "skill_gaps": [],
            "messages": [],
            "errors": [],
            "interview_type": interview_type,
            "difficulty": difficulty,
            "num_questions": num_questions
        }

        try:
            final_state = await self.workflow.ainvoke(initial_state)

            response = {
                "success": len(final_state["errors"]) == 0,
                "user_id": user_id,
                "job_id": job_id,
                "session_id": final_state.get("session_id"),
                "interview_plan": final_state.get("interview_plan"),
                "prep_tips": final_state.get("prep_tips", []),
                "focus_areas": final_state.get("focus_areas", []),
                "skill_gaps": final_state.get("skill_gaps", []),
                "questions_generated": final_state.get("questions_generated", 0),
                "messages": final_state["messages"],
                "errors": final_state["errors"],
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Interview Prep completed for user {user_id}: "
                f"session={final_state.get('session_id')}, "
                f"tips={len(final_state.get('prep_tips', []))}"
            )

            return response

        except Exception as e:
            logger.error(f"Interview Prep agent failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": initial_state["messages"],
                "errors": initial_state["errors"] + [str(e)]
            }
