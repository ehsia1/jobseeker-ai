"""Auto-Apply Agent.

This agent assists with automated job application submission:
1. Parse job requirements and assess fit
2. Customize resume and cover letter for the role
3. Prepare application materials
4. Generate form-filling data
5. Track application status and suggest follow-ups
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from backend.services.llm_service import get_llm_service


logger = logging.getLogger(__name__)


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def find_balanced_json(text: str) -> str:
    """Find the first balanced JSON object in text by counting braces."""
    start_idx = text.find('{')
    if start_idx == -1:
        return ""

    brace_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start_idx:], start=start_idx):
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start_idx:i+1]

    return text[start_idx:]


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling various formats."""
    if not text:
        logger.warning("extract_json received empty text")
        return {}

    content = text.strip()

    # Try to extract JSON from code blocks first
    if "```" in content:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            content = json_match.group(1).strip()

    # Find balanced JSON object
    content = find_balanced_json(content) if content else ""

    if not content:
        logger.warning("No JSON object found in text")
        return {}

    # Remove JavaScript-style comments
    def remove_comments(text: str) -> str:
        result = []
        i = 0
        while i < len(text):
            if text[i] == '"':
                j = i + 1
                while j < len(text):
                    if text[j] == '\\' and j + 1 < len(text):
                        j += 2
                        continue
                    if text[j] == '"':
                        break
                    j += 1
                result.append(text[i:j+1])
                i = j + 1
            elif text[i:i+2] == '//':
                j = i + 2
                while j < len(text) and text[j] != '\n':
                    j += 1
                i = j
            elif text[i:i+2] == '/*':
                j = i + 2
                while j < len(text) - 1 and text[j:j+2] != '*/':
                    j += 1
                i = j + 2
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    content = remove_comments(content)

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


class AutoApplyState(TypedDict):
    """State for Auto-Apply Agent."""
    # Input
    user_id: str
    job_url: Optional[str]
    job_title: str
    company_name: str
    job_description: str
    application_type: str  # quick_apply, custom, or full_form

    # User profile data
    user_name: str
    user_email: str
    user_phone: str
    user_location: str
    user_skills: List[str]
    user_experience: List[Dict[str, Any]]
    user_education: List[Dict[str, str]]
    resume_text: str

    # Analysis results
    job_requirements: Dict[str, Any]
    fit_assessment: Dict[str, Any]

    # Application materials
    customized_resume_points: List[str]
    cover_letter: str
    form_data: Dict[str, Any]
    screening_questions: List[Dict[str, Any]]

    # Follow-up plan
    follow_up_plan: Dict[str, Any]

    # Metadata
    application_score: float
    messages: List[str]
    errors: List[str]


class AutoApplyAgent:
    """Agent for automating job application preparation and submission."""

    def __init__(self):
        self.llm_service = None
        self.graph = self._build_graph()

    def _get_llm(self):
        """Get LLM service lazily."""
        if self.llm_service is None:
            self.llm_service = get_llm_service()
        return self.llm_service

    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph."""
        workflow = StateGraph(AutoApplyState)

        # Add nodes
        workflow.add_node("analyze_job", self._analyze_job)
        workflow.add_node("assess_fit", self._assess_fit)
        workflow.add_node("customize_materials", self._customize_materials)
        workflow.add_node("generate_form_data", self._generate_form_data)
        workflow.add_node("prepare_follow_up", self._prepare_follow_up)

        # Define edges
        workflow.set_entry_point("analyze_job")
        workflow.add_edge("analyze_job", "assess_fit")
        workflow.add_edge("assess_fit", "customize_materials")
        workflow.add_edge("customize_materials", "generate_form_data")
        workflow.add_edge("generate_form_data", "prepare_follow_up")
        workflow.add_edge("prepare_follow_up", END)

        return workflow.compile()

    async def run(
        self,
        user_id: str,
        job_title: str,
        company_name: str,
        job_description: str,
        job_url: Optional[str] = None,
        application_type: str = "custom",
        status_callback=None
    ) -> Dict[str, Any]:
        """Run the auto-apply agent."""

        def update_status(message: str):
            if status_callback:
                status_callback(message)
            logger.info(f"Auto-Apply Agent: {message}")

        update_status("Starting application preparation...")

        # Load user profile
        user_data = await self._load_user_profile(user_id)
        update_status(f"Profile loaded: {user_data.get('user_name', 'Unknown')}")

        # Initialize state
        initial_state: AutoApplyState = {
            "user_id": user_id,
            "job_url": job_url,
            "job_title": job_title,
            "company_name": company_name,
            "job_description": job_description,
            "application_type": application_type,
            **user_data,
            "job_requirements": {},
            "fit_assessment": {},
            "customized_resume_points": [],
            "cover_letter": "",
            "form_data": {},
            "screening_questions": [],
            "follow_up_plan": {},
            "application_score": 0.0,
            "messages": ["Agent initialized"],
            "errors": [],
        }

        # Run the workflow
        try:
            update_status("Analyzing job requirements...")
            result = await self.graph.ainvoke(initial_state)
            update_status(f"Completed! Application readiness: {result.get('application_score', 0):.0f}/100")
            return result
        except Exception as e:
            logger.error(f"Auto-Apply Agent error: {e}")
            initial_state["errors"].append(str(e))
            return initial_state

    async def _load_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Load user profile and resume data."""
        try:
            async with async_session() as session:
                # Load user with profile
                stmt = (
                    select(User)
                    .options(selectinload(User.profile))
                    .where(User.id == user_id)
                )
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    return {
                        "user_name": "Job Seeker",
                        "user_email": "",
                        "user_phone": "",
                        "user_location": "",
                        "user_skills": [],
                        "user_experience": [],
                        "user_education": [],
                        "resume_text": "",
                    }

                profile = user.profile

                # Load resume
                resume_stmt = (
                    select(Resume)
                    .where(Resume.user_id == user_id)
                    .order_by(Resume.created_at.desc())
                    .limit(1)
                )
                resume_result = await session.execute(resume_stmt)
                resume = resume_result.scalar_one_or_none()

                # Build user data
                user_data = {
                    "user_name": user.username,
                    "user_email": user.email or "",
                    "user_phone": profile.phone if profile else "",
                    "user_location": profile.location if profile else "",
                    "user_skills": profile.skills if profile and profile.skills else [],
                    "user_experience": [],  # Would parse from resume
                    "user_education": [],   # Would parse from resume
                    "resume_text": resume.content if resume else "",
                }

                return user_data

        except Exception as e:
            logger.error(f"Error loading user profile: {e}")
            return {
                "user_name": "Job Seeker",
                "user_email": "",
                "user_phone": "",
                "user_location": "",
                "user_skills": [],
                "user_experience": [],
                "user_education": [],
                "resume_text": "",
            }

    async def _analyze_job(self, state: AutoApplyState) -> AutoApplyState:
        """Analyze job posting to extract requirements."""
        try:
            llm = self._get_llm()

            prompt = f"""Analyze this job posting and extract structured requirements.

Job Title: {state["job_title"]}
Company: {state["company_name"]}
Job Description:
{state["job_description"][:3000]}

Return a JSON object with:
{{
    "required_skills": ["list of required technical skills"],
    "preferred_skills": ["list of preferred/nice-to-have skills"],
    "experience_years": "required years of experience or range",
    "education_requirements": "degree requirements",
    "key_responsibilities": ["main job responsibilities"],
    "must_have_qualifications": ["non-negotiable requirements"],
    "keywords": ["important keywords for ATS"],
    "company_values": ["inferred company values from posting"],
    "role_level": "entry/mid/senior/lead/executive",
    "remote_policy": "onsite/hybrid/remote/unspecified",
    "salary_range": "if mentioned in posting",
    "application_deadline": "if mentioned"
}}"""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["job_requirements"] = data
            state["messages"].append("Job requirements analyzed")

        except Exception as e:
            logger.error(f"Job analysis error: {e}")
            state["errors"].append(f"Job analysis error: {str(e)}")
            state["job_requirements"] = {
                "required_skills": [],
                "preferred_skills": [],
                "experience_years": "Not specified",
                "education_requirements": "Not specified",
                "key_responsibilities": [],
                "must_have_qualifications": [],
                "keywords": [],
            }

        return state

    async def _assess_fit(self, state: AutoApplyState) -> AutoApplyState:
        """Assess how well the user fits the role."""
        try:
            llm = self._get_llm()

            skills_text = ", ".join(state["user_skills"]) if state["user_skills"] else "Not specified"
            requirements = state["job_requirements"]

            prompt = f"""Assess how well this candidate fits the job requirements.

Candidate Profile:
- Name: {state["user_name"]}
- Skills: {skills_text}
- Location: {state["user_location"]}
- Resume Summary: {state["resume_text"][:1500] if state["resume_text"] else "No resume provided"}

Job Requirements:
- Required Skills: {', '.join(requirements.get('required_skills', []))}
- Preferred Skills: {', '.join(requirements.get('preferred_skills', []))}
- Experience: {requirements.get('experience_years', 'Not specified')}
- Education: {requirements.get('education_requirements', 'Not specified')}
- Role Level: {requirements.get('role_level', 'Not specified')}

Return a JSON object with:
{{
    "overall_match_score": 0-100,
    "skills_match": {{
        "score": 0-100,
        "matched_skills": ["skills candidate has"],
        "missing_skills": ["skills candidate lacks"],
        "transferable_skills": ["related skills that could apply"]
    }},
    "experience_match": {{
        "score": 0-100,
        "assessment": "brief assessment of experience fit"
    }},
    "strengths": ["candidate's strengths for this role"],
    "gaps": ["areas where candidate may fall short"],
    "positioning_strategy": "how to position this candidate best",
    "red_flags": ["potential concerns to address"],
    "interview_likelihood": "high/medium/low with reasoning",
    "recommendation": "apply/proceed_with_caution/consider_alternatives"
}}"""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["fit_assessment"] = data
            state["application_score"] = safe_float(data.get("overall_match_score"), 50)
            state["messages"].append(f"Fit assessed: {state['application_score']:.0f}% match")

        except Exception as e:
            logger.error(f"Fit assessment error: {e}")
            state["errors"].append(f"Fit assessment error: {str(e)}")
            state["fit_assessment"] = {
                "overall_match_score": 50,
                "skills_match": {"score": 50, "matched_skills": [], "missing_skills": []},
                "strengths": [],
                "gaps": [],
                "recommendation": "proceed_with_caution",
            }
            state["application_score"] = 50

        return state

    async def _customize_materials(self, state: AutoApplyState) -> AutoApplyState:
        """Generate customized resume points and cover letter."""
        try:
            llm = self._get_llm()

            requirements = state["job_requirements"]
            fit = state["fit_assessment"]

            prompt = f"""Create customized application materials for this job.

Job: {state["job_title"]} at {state["company_name"]}
Key Requirements: {', '.join(requirements.get('required_skills', [])[:5])}
Important Keywords: {', '.join(requirements.get('keywords', [])[:10])}
Candidate Strengths: {', '.join(fit.get('strengths', [])[:5])}
Positioning Strategy: {fit.get('positioning_strategy', 'Highlight relevant experience')}

Candidate Info:
- Name: {state["user_name"]}
- Skills: {', '.join(state["user_skills"][:10]) if state["user_skills"] else "Not specified"}
- Resume: {state["resume_text"][:1000] if state["resume_text"] else "Not provided"}

Return a JSON object with:
{{
    "resume_bullet_points": [
        "Achievement-focused bullet points emphasizing relevant experience",
        "Each point should use keywords from job posting",
        "Include metrics where possible"
    ],
    "skills_to_highlight": ["most relevant skills to emphasize"],
    "cover_letter": "A compelling 3-paragraph cover letter that: 1) Shows enthusiasm and understanding of the role, 2) Highlights 2-3 key qualifications with examples, 3) Expresses interest in next steps. Use professional but personable tone.",
    "key_achievements_to_mention": ["specific achievements relevant to this role"],
    "ats_optimization_tips": ["tips for passing ATS screening"]
}}"""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["customized_resume_points"] = data.get("resume_bullet_points", [])
            state["cover_letter"] = data.get("cover_letter", "")
            state["messages"].append("Application materials customized")

        except Exception as e:
            logger.error(f"Material customization error: {e}")
            state["errors"].append(f"Material customization error: {str(e)}")
            state["customized_resume_points"] = []
            state["cover_letter"] = ""

        return state

    async def _generate_form_data(self, state: AutoApplyState) -> AutoApplyState:
        """Generate data for common application form fields."""
        try:
            llm = self._get_llm()

            prompt = f"""Generate responses for common job application form fields.

Job: {state["job_title"]} at {state["company_name"]}
Candidate: {state["user_name"]}
Skills: {', '.join(state["user_skills"][:10]) if state["user_skills"] else "Not specified"}
Location: {state["user_location"]}

Generate professional responses for:

Return a JSON object with:
{{
    "form_fields": {{
        "desired_salary": "competitive salary expectation or range",
        "start_date": "available start date",
        "work_authorization": "authorization status response",
        "willing_to_relocate": "yes/no with context",
        "linkedin_url": "placeholder or actual URL",
        "portfolio_url": "placeholder or actual URL",
        "years_of_experience": "relevant experience years",
        "highest_education": "highest degree level"
    }},
    "screening_questions": [
        {{
            "question": "Why are you interested in this role?",
            "answer": "Compelling 2-3 sentence answer"
        }},
        {{
            "question": "What makes you a good fit for this position?",
            "answer": "Compelling 2-3 sentence answer"
        }},
        {{
            "question": "Describe a challenging project you've worked on",
            "answer": "STAR-format response"
        }},
        {{
            "question": "What are your salary expectations?",
            "answer": "Professional response about compensation"
        }},
        {{
            "question": "When can you start?",
            "answer": "Professional availability response"
        }}
    ]
}}"""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["form_data"] = data.get("form_fields", {})
            state["screening_questions"] = data.get("screening_questions", [])
            state["messages"].append(f"Generated {len(state['screening_questions'])} screening question responses")

        except Exception as e:
            logger.error(f"Form data generation error: {e}")
            state["errors"].append(f"Form data generation error: {str(e)}")
            state["form_data"] = {}
            state["screening_questions"] = []

        return state

    async def _prepare_follow_up(self, state: AutoApplyState) -> AutoApplyState:
        """Prepare follow-up strategy and timeline."""
        try:
            llm = self._get_llm()

            prompt = f"""Create a follow-up strategy for this job application.

Job: {state["job_title"]} at {state["company_name"]}
Application Score: {state["application_score"]:.0f}/100
Fit Assessment: {state["fit_assessment"].get('recommendation', 'apply')}

Create a follow-up plan:

Return a JSON object with:
{{
    "application_submitted": "{datetime.now().strftime('%Y-%m-%d')}",
    "follow_up_timeline": [
        {{
            "day": 7,
            "action": "Send follow-up email",
            "template": "Brief follow-up email template"
        }},
        {{
            "day": 14,
            "action": "LinkedIn connection request",
            "template": "Connection request message"
        }},
        {{
            "day": 21,
            "action": "Final follow-up",
            "template": "Final follow-up email template"
        }}
    ],
    "recruiter_outreach": {{
        "suggested_message": "Template for reaching out to recruiters",
        "best_platforms": ["platforms to find recruiters"]
    }},
    "interview_prep_tasks": [
        "Key preparation tasks if called for interview"
    ],
    "backup_actions": [
        "Alternative actions if no response"
    ],
    "success_indicators": ["signs the application is progressing"]
}}"""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["follow_up_plan"] = data
            state["messages"].append("Follow-up plan prepared")

            # Calculate final score considering all factors
            fit_score = safe_float(state["fit_assessment"].get("overall_match_score"), 50)
            materials_quality = 70 if state["cover_letter"] else 50
            form_completeness = min(100, len(state["screening_questions"]) * 20)

            state["application_score"] = (fit_score * 0.5 + materials_quality * 0.3 + form_completeness * 0.2)

        except Exception as e:
            logger.error(f"Follow-up preparation error: {e}")
            state["errors"].append(f"Follow-up preparation error: {str(e)}")
            state["follow_up_plan"] = {
                "follow_up_timeline": [],
                "interview_prep_tasks": [],
            }

        return state


# Singleton instance
_agent_instance = None


def get_auto_apply_agent() -> AutoApplyAgent:
    """Get or create the Auto-Apply Agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AutoApplyAgent()
    return _agent_instance


async def run_auto_apply_agent(
    user_id: str,
    job_title: str,
    company_name: str,
    job_description: str,
    job_url: Optional[str] = None,
    application_type: str = "custom",
    status_callback=None
) -> Dict[str, Any]:
    """Run the Auto-Apply Agent."""
    agent = get_auto_apply_agent()
    return await agent.run(
        user_id=user_id,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description,
        job_url=job_url,
        application_type=application_type,
        status_callback=status_callback
    )
