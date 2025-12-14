"""Network Intelligence Agent.

This agent helps users find connections and networking opportunities at target companies:
1. Analyze target company and role
2. Identify potential connection types (alumni, industry peers, recruiters)
3. Find networking opportunities
4. Generate personalized outreach strategies
5. Create networking action plan
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

    # If we didn't find balanced JSON, return everything from start
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
    if not content.startswith('{'):
        content = find_balanced_json(content)
    else:
        # Even if it starts with {, find balanced end
        content = find_balanced_json(content)

    if not content:
        logger.warning("No JSON object found in text")
        return {}

    # Remove JavaScript-style comments (// ... and /* ... */)
    # First, preserve strings then remove comments
    def remove_comments(text: str) -> str:
        result = []
        i = 0
        while i < len(text):
            # Handle strings (preserve them)
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
            # Handle // comments
            elif text[i:i+2] == '//':
                # Skip to end of line
                j = i + 2
                while j < len(text) and text[j] != '\n':
                    j += 1
                i = j
            # Handle /* */ comments
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


class NetworkIntelligenceState(TypedDict):
    """State for Network Intelligence Agent."""
    # Input
    user_id: str
    target_company: str
    target_role: Optional[str]
    target_industry: str
    networking_goals: List[str]

    # User profile
    user_name: str
    user_title: str
    user_location: str
    user_skills: List[str]
    user_education: List[Dict[str, str]]
    user_experience: List[Dict[str, Any]]

    # Company intelligence
    company_info: Dict[str, Any]
    company_culture: Dict[str, Any]
    hiring_trends: Dict[str, Any]

    # Connection opportunities
    connection_types: List[Dict[str, Any]]
    potential_contacts: List[Dict[str, Any]]
    alumni_connections: List[Dict[str, Any]]
    industry_connections: List[Dict[str, Any]]
    recruiter_insights: List[Dict[str, Any]]

    # Outreach strategy
    outreach_templates: List[Dict[str, Any]]
    conversation_starters: List[str]
    follow_up_strategies: List[Dict[str, Any]]

    # Networking plan
    action_plan: Dict[str, Any]
    networking_events: List[Dict[str, Any]]
    online_communities: List[Dict[str, Any]]
    content_strategy: Dict[str, Any]

    # Analysis
    networking_score: float
    warm_introduction_paths: List[Dict[str, Any]]
    mutual_interests: List[str]
    talking_points: List[str]

    # Agent state
    messages: List[str]
    errors: List[str]
    current_step: str


class NetworkIntelligenceAgent:
    """Agent for finding connections and networking opportunities at target companies."""

    def __init__(self):
        self.llm_service = None
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the agent graph."""
        workflow = StateGraph(NetworkIntelligenceState)

        # Add nodes
        workflow.add_node("load_user_profile", self.load_user_profile)
        workflow.add_node("research_company", self.research_company)
        workflow.add_node("identify_connection_types", self.identify_connection_types)
        workflow.add_node("find_networking_opportunities", self.find_networking_opportunities)
        workflow.add_node("generate_outreach_strategy", self.generate_outreach_strategy)
        workflow.add_node("create_action_plan", self.create_action_plan)

        # Define edges
        workflow.set_entry_point("load_user_profile")
        workflow.add_edge("load_user_profile", "research_company")
        workflow.add_edge("research_company", "identify_connection_types")
        workflow.add_edge("identify_connection_types", "find_networking_opportunities")
        workflow.add_edge("find_networking_opportunities", "generate_outreach_strategy")
        workflow.add_edge("generate_outreach_strategy", "create_action_plan")
        workflow.add_edge("create_action_plan", END)

        return workflow.compile()

    def _get_llm(self):
        """Get LLM service instance."""
        if self.llm_service is None:
            self.llm_service = get_llm_service()  # Not async
        return self.llm_service

    async def load_user_profile(self, state: NetworkIntelligenceState) -> NetworkIntelligenceState:
        """Load user profile and experience data."""
        state["current_step"] = "load_user_profile"
        state["messages"].append("Loading user profile...")

        try:
            async with async_session() as session:
                # Load user with profile and resume
                result = await session.execute(
                    select(User)
                    .options(selectinload(User.profile))
                    .where(User.id == state["user_id"])
                )
                user = result.scalar_one_or_none()

                if user and user.profile:
                    state["user_name"] = user.username
                    state["user_title"] = user.profile.job_title or "Professional"
                    state["user_location"] = user.profile.location or ""
                    state["user_skills"] = user.profile.skills or []
                elif user:
                    state["user_name"] = user.username
                    state["user_title"] = "Professional"
                    state["user_location"] = ""
                    state["user_skills"] = []
                else:
                    state["user_name"] = "Job Seeker"
                    state["user_title"] = "Professional"
                    state["user_location"] = ""
                    state["user_skills"] = []

                # Load resume for experience and education
                resume_result = await session.execute(
                    select(Resume).where(Resume.user_id == state["user_id"])
                )
                resume = resume_result.scalar_one_or_none()

                if resume and resume.parsed_data:
                    parsed = resume.parsed_data
                    state["user_education"] = parsed.get("education", [])
                    state["user_experience"] = parsed.get("experience", [])
                    if not state["user_skills"]:
                        state["user_skills"] = parsed.get("skills", [])
                else:
                    state["user_education"] = []
                    state["user_experience"] = []

                state["messages"].append(f"Profile loaded: {state['user_name']}")

        except Exception as e:
            logger.error(f"Error loading user profile: {e}")
            state["errors"].append(f"Profile loading error: {str(e)}")
            state["user_name"] = "Job Seeker"
            state["user_title"] = "Professional"
            state["user_location"] = ""
            state["user_skills"] = []
            state["user_education"] = []
            state["user_experience"] = []

        return state

    async def research_company(self, state: NetworkIntelligenceState) -> NetworkIntelligenceState:
        """Research target company for networking context."""
        state["current_step"] = "research_company"
        state["messages"].append(f"Researching {state['target_company']}...")

        try:
            llm = self._get_llm()

            prompt = f"""Analyze this target company for networking purposes.

Target Company: {state["target_company"]}
Target Role: {state.get("target_role", "Not specified")}
Industry: {state["target_industry"]}

User Background:
- Current/Desired Title: {state["user_title"]}
- Skills: {", ".join(state["user_skills"][:10]) if state["user_skills"] else "Not specified"}
- Location: {state["user_location"] or "Not specified"}

Provide company intelligence for networking in this JSON format:
{{
    "company_info": {{
        "size": "startup/medium/large/enterprise",
        "industry_focus": "primary industry focus",
        "key_departments": ["list of key departments"],
        "headquarters": "location",
        "remote_culture": "remote-first/hybrid/in-office",
        "growth_stage": "early/growth/mature",
        "recent_news": ["recent company news relevant for conversation"]
    }},
    "company_culture": {{
        "values": ["core company values"],
        "work_style": "description of work style",
        "employee_reviews_themes": ["common themes from employee feedback"],
        "innovation_focus": "how company approaches innovation",
        "diversity_initiatives": ["notable D&I programs"]
    }},
    "hiring_trends": {{
        "current_openings_estimate": "low/medium/high",
        "hot_skills": ["skills company is actively seeking"],
        "typical_hiring_process": "description of hiring process",
        "interview_style": "behavioral/technical/case study/mixed",
        "growth_areas": ["teams or areas that are expanding"]
    }}
}}

Provide realistic, actionable insights based on typical companies in this industry."""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["company_info"] = data.get("company_info", {})
            state["company_culture"] = data.get("company_culture", {})
            state["hiring_trends"] = data.get("hiring_trends", {})

            state["messages"].append("Company research complete")

        except Exception as e:
            logger.error(f"Error researching company: {e}")
            state["errors"].append(f"Company research error: {str(e)}")
            state["company_info"] = {}
            state["company_culture"] = {}
            state["hiring_trends"] = {}

        return state

    async def identify_connection_types(self, state: NetworkIntelligenceState) -> NetworkIntelligenceState:
        """Identify types of connections to pursue."""
        state["current_step"] = "identify_connection_types"
        state["messages"].append("Identifying potential connection types...")

        try:
            llm = self._get_llm()

            # Build education context
            education_context = []
            for edu in state["user_education"][:3]:
                school = edu.get("school", edu.get("institution", ""))
                degree = edu.get("degree", "")
                if school:
                    education_context.append(f"{degree} from {school}")

            # Build experience context
            experience_context = []
            for exp in state["user_experience"][:3]:
                company = exp.get("company", "")
                title = exp.get("title", "")
                if company:
                    experience_context.append(f"{title} at {company}")

            prompt = f"""Identify the best types of connections to pursue at the target company.

Target Company: {state["target_company"]}
Target Role: {state.get("target_role", "Not specified")}
Industry: {state["target_industry"]}

User Profile:
- Name: {state["user_name"]}
- Title: {state["user_title"]}
- Location: {state["user_location"] or "Not specified"}
- Skills: {", ".join(state["user_skills"][:10]) if state["user_skills"] else "Not specified"}
- Education: {"; ".join(education_context) if education_context else "Not specified"}
- Experience: {"; ".join(experience_context) if experience_context else "Not specified"}

Company Context:
- Size: {state["company_info"].get("size", "unknown")}
- Culture: {state["company_culture"].get("work_style", "unknown")}

Identify connection types in this JSON format:
{{
    "connection_types": [
        {{
            "type": "alumni/industry_peer/recruiter/hiring_manager/team_member/executive",
            "priority": "high/medium/low",
            "rationale": "why this connection type is valuable",
            "where_to_find": ["platforms or places to find this type"],
            "approach_style": "how to approach this type of contact",
            "expected_value": "what you can gain from this connection"
        }}
    ],
    "alumni_connections": [
        {{
            "school_or_company": "shared institution or company",
            "connection_strength": "strong/medium/weak",
            "outreach_angle": "how to leverage this shared background",
            "suggested_platforms": ["LinkedIn", "alumni networks", etc.]
        }}
    ],
    "industry_connections": [
        {{
            "connection_type": "conference attendee/community member/content creator/etc.",
            "relevance": "why this connection is relevant",
            "how_to_connect": "specific approach to make contact",
            "common_ground": ["shared interests or topics"]
        }}
    ],
    "recruiter_insights": [
        {{
            "recruiter_type": "internal/agency/executive",
            "how_to_find": "where to identify these recruiters",
            "approach_timing": "best time to reach out",
            "what_they_value": "what makes candidates stand out to them"
        }}
    ],
    "mutual_interests": ["list of topics/interests that could create connection"],
    "networking_score": 0.0  // 0-100 based on how strong user's potential network reach is
}}

Provide actionable, specific recommendations based on the user's actual background."""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["connection_types"] = data.get("connection_types", [])
            state["alumni_connections"] = data.get("alumni_connections", [])
            state["industry_connections"] = data.get("industry_connections", [])
            state["recruiter_insights"] = data.get("recruiter_insights", [])
            state["mutual_interests"] = data.get("mutual_interests", [])
            state["networking_score"] = safe_float(data.get("networking_score", 50.0))

            state["messages"].append(f"Identified {len(state['connection_types'])} connection types")

        except Exception as e:
            logger.error(f"Error identifying connections: {e}")
            state["errors"].append(f"Connection identification error: {str(e)}")
            state["connection_types"] = []
            state["alumni_connections"] = []
            state["industry_connections"] = []
            state["recruiter_insights"] = []
            state["mutual_interests"] = []
            state["networking_score"] = 0.0

        return state

    async def find_networking_opportunities(self, state: NetworkIntelligenceState) -> NetworkIntelligenceState:
        """Find specific networking opportunities and events."""
        state["current_step"] = "find_networking_opportunities"
        state["messages"].append("Finding networking opportunities...")

        try:
            llm = self._get_llm()

            prompt = f"""Find specific networking opportunities for reaching the target company.

Target Company: {state["target_company"]}
Target Role: {state.get("target_role", "Not specified")}
Industry: {state["target_industry"]}

User Profile:
- Title: {state["user_title"]}
- Skills: {", ".join(state["user_skills"][:8]) if state["user_skills"] else "Not specified"}
- Location: {state["user_location"] or "Flexible"}

Networking Goals: {", ".join(state["networking_goals"]) if state["networking_goals"] else "Build connections"}

Provide networking opportunities in this JSON format:
{{
    "networking_events": [
        {{
            "event_type": "conference/meetup/webinar/career_fair/hackathon",
            "name": "specific event name or type",
            "frequency": "annual/monthly/weekly/one-time",
            "relevance": "why this is valuable for target company",
            "how_to_maximize": "tips for getting value from this event",
            "likely_attendees": ["types of people who attend"],
            "cost": "free/low/medium/high",
            "location_type": "virtual/in-person/hybrid"
        }}
    ],
    "online_communities": [
        {{
            "platform": "LinkedIn/Slack/Discord/Reddit/Twitter/GitHub",
            "community_name": "specific community or group name",
            "activity_level": "very_active/active/moderate",
            "member_profile": "who typically participates",
            "engagement_strategy": "how to become a valued member",
            "connection_potential": "high/medium/low"
        }}
    ],
    "content_strategy": {{
        "platforms": ["best platforms for visibility"],
        "content_types": ["types of content to create or share"],
        "topics": ["topics that would attract target connections"],
        "posting_frequency": "recommended posting schedule",
        "engagement_tactics": ["how to engage with target company content"],
        "hashtags_or_keywords": ["relevant hashtags or keywords to use"]
    }},
    "potential_contacts": [
        {{
            "role_type": "specific role or title to target",
            "department": "which department",
            "seniority": "junior/mid/senior/executive",
            "value_proposition": "what you can offer this contact",
            "ask": "what you can ask for",
            "approach_platform": "where to reach out"
        }}
    ],
    "warm_introduction_paths": [
        {{
            "path": "description of connection chain",
            "starting_point": "where to begin",
            "intermediate_steps": ["steps to get introduction"],
            "success_likelihood": "high/medium/low",
            "time_estimate": "how long this path typically takes"
        }}
    ]
}}

Focus on realistic, actionable opportunities that the user can pursue immediately."""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["networking_events"] = data.get("networking_events", [])
            state["online_communities"] = data.get("online_communities", [])
            state["content_strategy"] = data.get("content_strategy", {})
            state["potential_contacts"] = data.get("potential_contacts", [])
            state["warm_introduction_paths"] = data.get("warm_introduction_paths", [])

            total_opportunities = (
                len(state["networking_events"]) +
                len(state["online_communities"]) +
                len(state["potential_contacts"])
            )
            state["messages"].append(f"Found {total_opportunities} networking opportunities")

        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
            state["errors"].append(f"Opportunity finding error: {str(e)}")
            state["networking_events"] = []
            state["online_communities"] = []
            state["content_strategy"] = {}
            state["potential_contacts"] = []
            state["warm_introduction_paths"] = []

        return state

    async def generate_outreach_strategy(self, state: NetworkIntelligenceState) -> NetworkIntelligenceState:
        """Generate personalized outreach templates and strategies."""
        state["current_step"] = "generate_outreach_strategy"
        state["messages"].append("Generating outreach strategy...")

        try:
            llm = self._get_llm()

            prompt = f"""Create personalized outreach strategies for networking at the target company.

Target Company: {state["target_company"]}
Target Role: {state.get("target_role", "Not specified")}
Industry: {state["target_industry"]}

User Profile:
- Name: {state["user_name"]}
- Title: {state["user_title"]}
- Key Skills: {", ".join(state["user_skills"][:5]) if state["user_skills"] else "Professional background"}

Company Culture: {state["company_culture"].get("work_style", "Professional")}
Values: {", ".join(state["company_culture"].get("values", [])) if state["company_culture"].get("values") else "Quality and innovation"}

Connection Types Identified: {[c.get("type") for c in state["connection_types"][:3]]}
Mutual Interests: {", ".join(state["mutual_interests"][:5]) if state["mutual_interests"] else "Industry trends"}

Create outreach templates in this JSON format:
{{
    "outreach_templates": [
        {{
            "scenario": "cold_outreach/warm_introduction/follow_up/informational_interview_request",
            "target_role": "who this template is for",
            "platform": "LinkedIn/email/Twitter",
            "subject_line": "subject line if email",
            "message": "the actual outreach message (personalized, authentic, not salesy)",
            "call_to_action": "specific ask",
            "tone": "professional/casual/enthusiastic",
            "length": "short/medium",
            "personalization_tips": ["how to customize this template"]
        }}
    ],
    "conversation_starters": [
        "specific conversation starter related to the company or industry"
    ],
    "follow_up_strategies": [
        {{
            "scenario": "no_response/positive_response/maybe_later/referral_received",
            "timing": "when to follow up",
            "approach": "how to follow up",
            "message_template": "brief follow-up message",
            "persistence_limit": "how many times to follow up"
        }}
    ],
    "talking_points": [
        "key talking points that demonstrate value and interest"
    ],
    "questions_to_ask": [
        {{
            "question": "thoughtful question to ask",
            "purpose": "what you learn from this question",
            "when_to_ask": "appropriate context for this question"
        }}
    ]
}}

Make templates authentic, specific to the company, and focused on building genuine relationships."""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["outreach_templates"] = data.get("outreach_templates", [])
            state["conversation_starters"] = data.get("conversation_starters", [])
            state["follow_up_strategies"] = data.get("follow_up_strategies", [])
            state["talking_points"] = data.get("talking_points", [])

            state["messages"].append(f"Created {len(state['outreach_templates'])} outreach templates")

        except Exception as e:
            logger.error(f"Error generating outreach strategy: {e}")
            state["errors"].append(f"Outreach strategy error: {str(e)}")
            state["outreach_templates"] = []
            state["conversation_starters"] = []
            state["follow_up_strategies"] = []
            state["talking_points"] = []

        return state

    async def create_action_plan(self, state: NetworkIntelligenceState) -> NetworkIntelligenceState:
        """Create a comprehensive networking action plan."""
        state["current_step"] = "create_action_plan"
        state["messages"].append("Creating networking action plan...")

        try:
            llm = self._get_llm()

            prompt = f"""Create a comprehensive networking action plan to connect with the target company.

Target Company: {state["target_company"]}
Target Role: {state.get("target_role", "Not specified")}
Networking Score: {state["networking_score"]:.0f}/100

Resources Available:
- Connection Types: {len(state["connection_types"])}
- Networking Events: {len(state["networking_events"])}
- Online Communities: {len(state["online_communities"])}
- Outreach Templates: {len(state["outreach_templates"])}
- Warm Introduction Paths: {len(state["warm_introduction_paths"])}

User Goals: {", ".join(state["networking_goals"]) if state["networking_goals"] else "Build meaningful connections"}

Create an action plan in this JSON format:
{{
    "action_plan": {{
        "immediate_actions": [
            {{
                "action": "specific action to take",
                "priority": "high/medium/low",
                "time_required": "estimated time",
                "expected_outcome": "what this achieves",
                "resources_needed": ["what you need"]
            }}
        ],
        "weekly_tasks": [
            {{
                "task": "recurring weekly task",
                "frequency": "times per week",
                "platform": "where to do this",
                "goal": "what you're trying to achieve"
            }}
        ],
        "milestone_targets": [
            {{
                "milestone": "target to achieve",
                "timeframe": "when to achieve by",
                "success_criteria": "how to know you've achieved it",
                "dependencies": ["what needs to happen first"]
            }}
        ],
        "metrics_to_track": [
            {{
                "metric": "what to measure",
                "target": "goal number or state",
                "tracking_method": "how to track"
            }}
        ],
        "risk_mitigation": [
            {{
                "risk": "potential obstacle",
                "mitigation": "how to address it"
            }}
        ]
    }},
    "quick_wins": ["actions that can yield fast results"],
    "long_term_investments": ["actions that build value over time"],
    "success_probability": 0.0,  // 0-100 estimated probability of successful connection
    "estimated_timeline": "realistic timeline to meaningful connection",
    "key_success_factors": ["what will make this successful"]
}}

Create a realistic, actionable plan that balances quick wins with long-term relationship building."""

            response = await llm.generate(prompt)
            data = extract_json(response.content)

            state["action_plan"] = data.get("action_plan", {})

            # Update networking score based on analysis
            success_prob = safe_float(data.get("success_probability", state["networking_score"]))
            state["networking_score"] = (state["networking_score"] + success_prob) / 2

            state["messages"].append(f"Action plan complete. Networking score: {state['networking_score']:.0f}/100")

        except Exception as e:
            logger.error(f"Error creating action plan: {e}")
            state["errors"].append(f"Action plan error: {str(e)}")
            state["action_plan"] = {}

        return state

    async def run(
        self,
        user_id: str,
        target_company: str,
        target_role: Optional[str] = None,
        target_industry: str = "technology",
        networking_goals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run the Network Intelligence Agent."""

        # Initialize state
        initial_state: NetworkIntelligenceState = {
            "user_id": user_id,
            "target_company": target_company,
            "target_role": target_role,
            "target_industry": target_industry,
            "networking_goals": networking_goals or ["Build connections", "Learn about opportunities"],

            "user_name": "",
            "user_title": "",
            "user_location": "",
            "user_skills": [],
            "user_education": [],
            "user_experience": [],

            "company_info": {},
            "company_culture": {},
            "hiring_trends": {},

            "connection_types": [],
            "potential_contacts": [],
            "alumni_connections": [],
            "industry_connections": [],
            "recruiter_insights": [],

            "outreach_templates": [],
            "conversation_starters": [],
            "follow_up_strategies": [],

            "action_plan": {},
            "networking_events": [],
            "online_communities": [],
            "content_strategy": {},

            "networking_score": 0.0,
            "warm_introduction_paths": [],
            "mutual_interests": [],
            "talking_points": [],

            "messages": [],
            "errors": [],
            "current_step": "initializing"
        }

        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)

            return {
                "target_company": target_company,
                "target_role": target_role,
                "target_industry": target_industry,

                "company_info": final_state.get("company_info", {}),
                "company_culture": final_state.get("company_culture", {}),
                "hiring_trends": final_state.get("hiring_trends", {}),

                "connection_types": final_state.get("connection_types", []),
                "potential_contacts": final_state.get("potential_contacts", []),
                "alumni_connections": final_state.get("alumni_connections", []),
                "industry_connections": final_state.get("industry_connections", []),
                "recruiter_insights": final_state.get("recruiter_insights", []),

                "outreach_templates": final_state.get("outreach_templates", []),
                "conversation_starters": final_state.get("conversation_starters", []),
                "follow_up_strategies": final_state.get("follow_up_strategies", []),
                "talking_points": final_state.get("talking_points", []),

                "action_plan": final_state.get("action_plan", {}),
                "networking_events": final_state.get("networking_events", []),
                "online_communities": final_state.get("online_communities", []),
                "content_strategy": final_state.get("content_strategy", {}),

                "networking_score": final_state.get("networking_score", 0.0),
                "warm_introduction_paths": final_state.get("warm_introduction_paths", []),
                "mutual_interests": final_state.get("mutual_interests", []),

                "messages": final_state.get("messages", []),
                "errors": final_state.get("errors", [])
            }

        except Exception as e:
            logger.error(f"Network Intelligence Agent error: {e}")
            return {
                "target_company": target_company,
                "target_role": target_role,
                "target_industry": target_industry,
                "company_info": {},
                "company_culture": {},
                "hiring_trends": {},
                "connection_types": [],
                "potential_contacts": [],
                "alumni_connections": [],
                "industry_connections": [],
                "recruiter_insights": [],
                "outreach_templates": [],
                "conversation_starters": [],
                "follow_up_strategies": [],
                "talking_points": [],
                "action_plan": {},
                "networking_events": [],
                "online_communities": [],
                "content_strategy": {},
                "networking_score": 0.0,
                "warm_introduction_paths": [],
                "mutual_interests": [],
                "messages": ["Agent encountered an error"],
                "errors": [str(e)]
            }
