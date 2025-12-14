"""Salary Research & Negotiation Agent.

This agent provides comprehensive salary research and negotiation support:
1. Market rate research for job titles and locations
2. Compensation package analysis (base, equity, bonus, benefits)
3. Personalized negotiation strategies based on user profile
4. Negotiation scripts and counter-offer templates
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
    original_content = content  # Keep for error logging

    # Try to extract JSON from code blocks
    if "```" in content:
        # Find JSON in code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            content = json_match.group(1).strip()

    # Try to find JSON object in the text
    if not content.startswith('{'):
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)

    # Clean up common LLM output issues
    # Remove trailing commas before closing braces/brackets
    content = re.sub(r',(\s*[}\]])', r'\1', content)

    # Fix dollar signs in unquoted numbers: $260,000 -> 260000
    # Match dollar sign followed by numbers (possibly with commas)
    content = re.sub(r'\$(\d[\d,]*)', r'\1', content)

    # Fix common number formatting issues (1,000 -> 1000)
    # But be careful not to break array commas
    # Only fix numbers with commas inside quotes or after colons
    content = re.sub(r'(\d),(\d{3})(?=[,}\]\s])', r'\1\2', content)
    content = re.sub(r'(\d),(\d{3})(?=[,}\]\s])', r'\1\2', content)  # Run twice for numbers like 1,000,000

    # Fix control characters inside string values
    # Replace literal newlines/tabs inside quotes with escaped versions
    def escape_control_chars(match):
        s = match.group(0)
        # Escape unescaped control characters inside the string
        s = s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return s

    # Match JSON string values and escape control chars inside them
    content = re.sub(r'"(?:[^"\\]|\\.)*"', escape_control_chars, content)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Content being parsed (first 500 chars): {content[:500]}")
        logger.error(f"Original text (first 500 chars): {original_content[:500]}")
        raise


from backend.database import async_session
from backend.models.user import User, UserProfile
from backend.models.resume import Resume

from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class SalaryAgentState(TypedDict, total=False):
    """State for the Salary Research Agent."""
    # Input
    user_id: str
    job_title: str
    location: str
    years_experience: int
    current_salary: Optional[float]
    target_salary: Optional[float]
    company_name: Optional[str]
    job_level: str  # entry, mid, senior, lead, executive
    include_negotiation_scripts: bool

    # Profile data
    profile_data: Dict[str, Any]
    resume_data: Dict[str, Any]

    # Research results
    market_data: Dict[str, Any]
    salary_range: Dict[str, float]  # min, median, max, p25, p75
    location_adjustment: float  # multiplier for location cost of living
    experience_adjustment: float  # multiplier for experience level

    # Compensation breakdown
    compensation_analysis: Dict[str, Any]
    total_comp_estimate: float

    # Negotiation
    negotiation_leverage: List[str]
    negotiation_strategy: Dict[str, Any]
    negotiation_scripts: List[Dict[str, str]]
    counter_offer_template: str

    # Output
    messages: List[str]
    errors: List[str]


# In-memory storage for run results
_salary_runs: Dict[str, Dict[str, Any]] = {}


def get_salary_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a salary research run by ID."""
    return _salary_runs.get(run_id)


def update_salary_run(run_id: str, updates: Dict[str, Any]) -> None:
    """Update a salary research run."""
    if run_id in _salary_runs:
        _salary_runs[run_id].update(updates)


class SalaryAgent:
    """Agent for salary research and negotiation coaching."""

    def __init__(self):
        self.llm_service = None
        self.graph = None

    async def initialize(self) -> None:
        """Initialize the agent with LLM and graph."""
        self.llm_service = get_llm_service()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(SalaryAgentState)

        # Add nodes
        workflow.add_node("load_user_data", self._load_user_data_node)
        workflow.add_node("research_market_rates", self._research_market_rates_node)
        workflow.add_node("analyze_compensation", self._analyze_compensation_node)
        workflow.add_node("calculate_adjustments", self._calculate_adjustments_node)
        workflow.add_node("build_negotiation_strategy", self._build_negotiation_strategy_node)
        workflow.add_node("generate_scripts", self._generate_scripts_node)
        workflow.add_node("finalize", self._finalize_node)

        # Set entry point
        workflow.set_entry_point("load_user_data")

        # Add edges
        workflow.add_edge("load_user_data", "research_market_rates")
        workflow.add_edge("research_market_rates", "analyze_compensation")
        workflow.add_edge("analyze_compensation", "calculate_adjustments")
        workflow.add_edge("calculate_adjustments", "build_negotiation_strategy")
        workflow.add_conditional_edges(
            "build_negotiation_strategy",
            lambda s: "generate_scripts" if s.get("include_negotiation_scripts", True) else "finalize",
            {"generate_scripts": "generate_scripts", "finalize": "finalize"}
        )
        workflow.add_edge("generate_scripts", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _load_user_data_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Load user profile and resume data."""
        messages = state.get("messages", [])
        messages.append("Loading user profile data...")

        user_id = state.get("user_id")
        profile_data = {}
        resume_data = {}

        if user_id:
            try:
                async with async_session() as session:
                    # Load user with profile and resume
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
                        profile_data = {
                            "current_role": profile.job_title,
                            "years_experience": profile.experience_years,
                            "skills": profile.skills or [],
                            "location": profile.location,
                        }

                        # Use profile years if not specified
                        if not state.get("years_experience") and profile.experience_years:
                            state["years_experience"] = profile.experience_years

                    if user and user.resume:
                        # User has one resume (one-to-one relationship)
                        resume = user.resume
                        if resume:
                            resume_data = {
                                "skills": resume.skills or [],
                                "education": resume.education or [],
                                "work_experiences": [],
                            }

                            # Load work experiences if available
                            if hasattr(resume, 'work_experiences'):
                                result = await session.execute(
                                    select(Resume)
                                    .options(selectinload(Resume.work_experiences))
                                    .where(Resume.id == resume.id)
                                )
                                resume_with_exp = result.scalar_one_or_none()
                                if resume_with_exp and resume_with_exp.work_experiences:
                                    for exp in resume_with_exp.work_experiences:
                                        resume_data["work_experiences"].append({
                                            "title": exp.title,
                                            "company": exp.company,
                                            "is_current": exp.end_date is None,
                                        })

            except Exception as e:
                logger.error(f"Error loading user data: {e}")
                messages.append(f"Note: Could not load user profile data")

        messages.append("Profile data loaded")

        return {
            "profile_data": profile_data,
            "resume_data": resume_data,
            "messages": messages,
        }

    async def _research_market_rates_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Research market salary rates for the job title and location."""
        messages = state.get("messages", [])
        messages.append("Researching market salary rates...")

        job_title = state.get("job_title", "Software Engineer")
        location = state.get("location", "Remote")
        years_exp = state.get("years_experience", 5)
        job_level = state.get("job_level", "mid")
        company_name = state.get("company_name")

        # Build research prompt
        prompt = f"""Research and estimate current market salary data for:

Job Title: {job_title}
Location: {location}
Experience Level: {years_exp} years
Job Level: {job_level}
{f'Company: {company_name}' if company_name else ''}

Provide realistic 2024/2025 salary data in this JSON format:
{{
    "base_salary": {{
        "min": <minimum base salary>,
        "p25": <25th percentile>,
        "median": <median salary>,
        "p75": <75th percentile>,
        "max": <maximum base salary>
    }},
    "total_compensation": {{
        "min": <minimum total comp>,
        "median": <median total comp>,
        "max": <maximum total comp>
    }},
    "typical_bonus_percent": <typical annual bonus as percentage>,
    "typical_equity_value": <typical annual equity value>,
    "market_demand": "<high/medium/low>",
    "salary_trend": "<increasing/stable/decreasing>",
    "key_factors": ["factor1", "factor2"],
    "data_sources": ["Based on industry knowledge of tech salaries in 2024"]
}}

Base your estimates on realistic current market data. Be conservative but accurate.
Return ONLY the JSON, no other text."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are a compensation research expert with deep knowledge of current tech salary markets. Provide accurate, realistic salary data."
            )

            market_data = extract_json(response.content)

            # Extract salary range
            base_salary = market_data.get("base_salary", {})
            salary_range = {
                "min": base_salary.get("min", 0),
                "p25": base_salary.get("p25", 0),
                "median": base_salary.get("median", 0),
                "p75": base_salary.get("p75", 0),
                "max": base_salary.get("max", 0),
            }

            messages.append(f"Market research complete - Median: ${safe_float(salary_range.get('median')):,.0f}")

            return {
                "market_data": market_data,
                "salary_range": salary_range,
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"Error researching market rates: {e}")
            messages.append(f"Error researching market rates")

            # Return sensible defaults
            return {
                "market_data": {},
                "salary_range": {
                    "min": 80000,
                    "p25": 100000,
                    "median": 120000,
                    "p75": 150000,
                    "max": 200000,
                },
                "messages": messages,
                "errors": state.get("errors", []) + [str(e)],
            }

    async def _analyze_compensation_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Analyze total compensation breakdown."""
        messages = state.get("messages", [])
        messages.append("Analyzing compensation components...")

        market_data = state.get("market_data", {})
        salary_range = state.get("salary_range", {})
        job_title = state.get("job_title", "Software Engineer")
        company_name = state.get("company_name")

        # Build compensation analysis prompt
        min_sal = safe_float(salary_range.get('min', 0))
        max_sal = safe_float(salary_range.get('max', 0))
        prompt = f"""Analyze total compensation for:
Job Title: {job_title}
{f'Company: {company_name}' if company_name else 'Company: Typical tech company'}
Base Salary Range: ${min_sal:,.0f} - ${max_sal:,.0f}

Provide a detailed compensation breakdown in JSON format:
{{
    "base_salary_weight": <percentage of total comp that is base, e.g., 70>,
    "equity_component": {{
        "typical_grant_value": <typical 4-year grant value>,
        "annual_value": <annual value after vesting>,
        "vesting_schedule": "4-year with 1-year cliff",
        "type": "RSU/Options/None"
    }},
    "bonus_component": {{
        "target_percent": <target bonus as percent of base>,
        "typical_range": "10-20%",
        "timing": "Annual"
    }},
    "benefits_value": {{
        "health_insurance": <annual value>,
        "401k_match": <annual value>,
        "other_benefits": <estimated value of other perks>,
        "total_annual": <total benefits value>
    }},
    "additional_perks": ["perk1", "perk2"],
    "remote_premium_or_discount": <percentage adjustment for remote vs office>,
    "negotiable_components": ["base salary", "signing bonus", "equity"]
}}

Return ONLY the JSON, no other text."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are a compensation analyst expert. Provide realistic compensation breakdowns for tech industry roles."
            )

            compensation_analysis = extract_json(response.content)

            # Calculate total comp estimate
            median_base = salary_range.get("median", 120000)
            bonus_percent = compensation_analysis.get("bonus_component", {}).get("target_percent", 10)
            equity_annual = compensation_analysis.get("equity_component", {}).get("annual_value", 0)
            benefits_annual = compensation_analysis.get("benefits_value", {}).get("total_annual", 20000)

            total_comp = median_base + (median_base * bonus_percent / 100) + equity_annual + benefits_annual

            messages.append(f"Total compensation estimated at ${total_comp:,.0f}")

            return {
                "compensation_analysis": compensation_analysis,
                "total_comp_estimate": total_comp,
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"Error analyzing compensation: {e}")
            return {
                "compensation_analysis": {},
                "total_comp_estimate": salary_range.get("median", 120000) * 1.3,
                "messages": messages,
                "errors": state.get("errors", []) + [str(e)],
            }

    async def _calculate_adjustments_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Calculate location and experience adjustments."""
        messages = state.get("messages", [])
        messages.append("Calculating personalized adjustments...")

        location = state.get("location", "Remote")
        years_exp = state.get("years_experience", 5)
        job_level = state.get("job_level", "mid")

        # Location cost of living adjustments (relative to national average = 1.0)
        location_adjustments = {
            # High cost
            "san francisco": 1.35,
            "new york": 1.30,
            "seattle": 1.20,
            "los angeles": 1.15,
            "boston": 1.15,
            # Medium cost
            "denver": 1.05,
            "austin": 1.05,
            "chicago": 1.00,
            "atlanta": 0.95,
            # Lower cost
            "remote": 1.00,
            "dallas": 0.90,
            "phoenix": 0.90,
        }

        # Find location adjustment
        location_lower = location.lower()
        location_adjustment = 1.0
        for loc, adj in location_adjustments.items():
            if loc in location_lower:
                location_adjustment = adj
                break

        # Experience level adjustments (relative to mid-level = 1.0)
        level_adjustments = {
            "entry": 0.70,
            "mid": 1.00,
            "senior": 1.25,
            "staff": 1.50,
            "lead": 1.40,
            "principal": 1.75,
            "executive": 2.00,
        }

        experience_adjustment = level_adjustments.get(job_level.lower(), 1.0)

        # Adjust for years of experience within level
        if years_exp > 10:
            experience_adjustment *= 1.10
        elif years_exp > 7:
            experience_adjustment *= 1.05

        messages.append(f"Location adjustment: {location_adjustment:.0%}, Experience adjustment: {experience_adjustment:.0%}")

        return {
            "location_adjustment": location_adjustment,
            "experience_adjustment": experience_adjustment,
            "messages": messages,
        }

    async def _build_negotiation_strategy_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Build personalized negotiation strategy."""
        messages = state.get("messages", [])
        messages.append("Building negotiation strategy...")

        current_salary = state.get("current_salary")
        target_salary = state.get("target_salary")
        salary_range = state.get("salary_range", {})
        market_data = state.get("market_data", {})
        profile_data = state.get("profile_data", {})
        resume_data = state.get("resume_data", {})

        # Build leverage points
        leverage_points = []

        skills = profile_data.get("skills", []) or resume_data.get("skills", [])
        if skills:
            leverage_points.append(f"Strong technical skills: {', '.join(skills[:5])}")

        work_exp = resume_data.get("work_experiences", [])
        if work_exp:
            leverage_points.append(f"Relevant work experience at {len(work_exp)} companies")

        if market_data.get("market_demand") == "high":
            leverage_points.append("High market demand for this role")

        if current_salary and salary_range.get("median"):
            if current_salary >= salary_range["median"]:
                leverage_points.append("Currently earning at or above market rate")
            else:
                leverage_points.append("Opportunity for significant salary increase to reach market rate")

        # Build strategy prompt
        current_salary_str = f"${safe_float(current_salary):,.0f}" if current_salary else "Not disclosed"
        target_salary_str = f"${safe_float(target_salary):,.0f}" if target_salary else "Market rate"
        median_sal = safe_float(salary_range.get('median'), 120000)
        p25_sal = safe_float(salary_range.get('p25'))
        p75_sal = safe_float(salary_range.get('p75'))

        prompt = f"""Create a negotiation strategy for:

Current Salary: {current_salary_str}
Target Salary: {target_salary_str}
Market Median: ${median_sal:,.0f}
Market Range: ${p25_sal:,.0f} - ${p75_sal:,.0f}

Leverage Points:
{chr(10).join(f'- {lp}' for lp in leverage_points)}

Provide a negotiation strategy in JSON format:
{{
    "recommended_ask": <recommended salary to ask for>,
    "walk_away_point": <minimum acceptable salary>,
    "anchor_high_rationale": "explanation of why to anchor high",
    "timing_advice": "when to discuss salary",
    "opening_approach": "how to start the negotiation",
    "key_talking_points": ["point1", "point2", "point3"],
    "common_objections": [
        {{"objection": "budget constraints", "response": "how to respond"}}
    ],
    "alternatives_to_negotiate": ["signing bonus", "extra PTO", "remote flexibility"],
    "risk_level": "<low/medium/high>",
    "confidence_score": <1-100 score of how strong your position is>
}}

Return ONLY the JSON, no other text."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert salary negotiation coach. Provide strategic, actionable negotiation advice."
            )

            negotiation_strategy = extract_json(response.content)

            recommended = float(negotiation_strategy.get('recommended_ask', 0) or 0)
            messages.append(f"Strategy built - Recommended ask: ${recommended:,.0f}")

            return {
                "negotiation_leverage": leverage_points,
                "negotiation_strategy": negotiation_strategy,
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"Error building negotiation strategy: {e}")
            return {
                "negotiation_leverage": leverage_points,
                "negotiation_strategy": {
                    "recommended_ask": salary_range.get("p75", 150000),
                    "walk_away_point": salary_range.get("p25", 100000),
                    "key_talking_points": ["Focus on value you bring", "Research the market", "Be confident"],
                },
                "messages": messages,
                "errors": state.get("errors", []) + [str(e)],
            }

    async def _generate_scripts_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Generate negotiation scripts and templates."""
        messages = state.get("messages", [])
        messages.append("Generating negotiation scripts...")

        job_title = state.get("job_title", "Software Engineer")
        company_name = state.get("company_name", "the company")
        negotiation_strategy = state.get("negotiation_strategy", {})
        recommended_ask = safe_float(negotiation_strategy.get("recommended_ask"), 150000)

        prompt = f"""Generate negotiation scripts for:
Job: {job_title}
Company: {company_name}
Target Salary: ${recommended_ask:,.0f}

Create 3 scripts in JSON format:
{{
    "scripts": [
        {{
            "scenario": "Initial salary discussion",
            "script": "Full script text...",
            "tone": "confident but collaborative"
        }},
        {{
            "scenario": "Responding to low offer",
            "script": "Full script text...",
            "tone": "professional and firm"
        }},
        {{
            "scenario": "Final negotiation push",
            "script": "Full script text...",
            "tone": "appreciative but assertive"
        }}
    ],
    "counter_offer_email_template": "Full email template for counter offer..."
}}

Make scripts sound natural and professional. Include specific dollar amounts.
Return ONLY the JSON, no other text."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are an expert at writing professional negotiation scripts that sound natural and confident."
            )

            result = extract_json(response.content)

            messages.append(f"Generated {len(result.get('scripts', []))} negotiation scripts")

            return {
                "negotiation_scripts": result.get("scripts", []),
                "counter_offer_template": result.get("counter_offer_email_template", ""),
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"Error generating scripts: {e}")
            return {
                "negotiation_scripts": [],
                "counter_offer_template": "",
                "messages": messages,
                "errors": state.get("errors", []) + [str(e)],
            }

    async def _finalize_node(self, state: SalaryAgentState) -> Dict[str, Any]:
        """Finalize results."""
        messages = state.get("messages", [])
        messages.append("Research complete!")
        return {"messages": messages}

    async def run(
        self,
        user_id: str,
        job_title: str,
        location: str = "Remote",
        years_experience: int = 5,
        current_salary: Optional[float] = None,
        target_salary: Optional[float] = None,
        company_name: Optional[str] = None,
        job_level: str = "mid",
        include_negotiation_scripts: bool = True,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the salary research agent."""
        if not self.graph:
            await self.initialize()

        if not run_id:
            run_id = str(uuid.uuid4())

        # Initialize run storage
        _salary_runs[run_id] = {
            "run_id": run_id,
            "status": "running",
            "user_id": user_id,
            "started_at": datetime.utcnow(),
            "progress_percent": 0,
            "current_step": "Initializing",
            "messages": [],
            "errors": [],
        }

        try:
            # Build initial state
            initial_state: SalaryAgentState = {
                "user_id": user_id,
                "job_title": job_title,
                "location": location,
                "years_experience": years_experience,
                "current_salary": current_salary,
                "target_salary": target_salary,
                "company_name": company_name,
                "job_level": job_level,
                "include_negotiation_scripts": include_negotiation_scripts,
                "messages": ["Starting Salary Research agent..."],
                "errors": [],
            }

            update_salary_run(run_id, {"current_step": "Loading data", "progress_percent": 10})

            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Update run with results
            _salary_runs[run_id].update({
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "progress_percent": 100,
                "current_step": "Complete",
                "messages": result.get("messages", []),
                "errors": result.get("errors", []),
                # Results
                "job_title": job_title,
                "location": location,
                "market_data": result.get("market_data", {}),
                "salary_range": result.get("salary_range", {}),
                "compensation_analysis": result.get("compensation_analysis", {}),
                "total_comp_estimate": result.get("total_comp_estimate", 0),
                "location_adjustment": result.get("location_adjustment", 1.0),
                "experience_adjustment": result.get("experience_adjustment", 1.0),
                "negotiation_leverage": result.get("negotiation_leverage", []),
                "negotiation_strategy": result.get("negotiation_strategy", {}),
                "negotiation_scripts": result.get("negotiation_scripts", []),
                "counter_offer_template": result.get("counter_offer_template", ""),
            })

            return _salary_runs[run_id]

        except Exception as e:
            logger.error(f"Salary agent error: {e}")
            _salary_runs[run_id].update({
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "errors": [str(e)],
            })
            return _salary_runs[run_id]


# Global agent instance
_salary_agent: Optional[SalaryAgent] = None


async def get_salary_agent() -> SalaryAgent:
    """Get or create the salary agent instance."""
    global _salary_agent
    if _salary_agent is None:
        _salary_agent = SalaryAgent()
        await _salary_agent.initialize()
    return _salary_agent
