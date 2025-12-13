"""JobRadar Agent - Main orchestration agent for job discovery and matching."""

import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the job search agent."""
    user_id: str
    user_profile: Optional[Dict[str, Any]]
    search_query: Optional[Dict[str, Any]]
    raw_jobs: List[Dict[str, Any]]
    scored_jobs: List[Dict[str, Any]]
    top_matches: List[Dict[str, Any]]
    proposals: Dict[str, str]  # job_id -> proposal
    notifications_sent: bool
    messages: List[str]
    errors: List[str]
    # Config
    min_score: float
    generate_proposals: bool
    max_proposals: int


class JobRadarAgent:
    """Main agent for job discovery and matching."""

    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize the JobRadar agent.

        Args:
            db: Optional database session for direct queries
        """
        self.db = db
        self.llm_provider = settings.llm_provider

        # Initialize LLM based on settings
        self.llm = self._init_llm()

        # Build the workflow graph
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
                logger.warning("langchain-ollama not installed, falling back to mock LLM")
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
                logger.warning("langchain-openai not installed")
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
                logger.warning("langchain-anthropic not installed")
                return self._get_mock_llm()
        else:
            return self._get_mock_llm()

    def _get_mock_llm(self):
        """Get a mock LLM for testing."""
        from langchain_community.llms import FakeListLLM
        return FakeListLLM(
            responses=["I'll help you find the best jobs."]
        )
    
    def _build_workflow(self):
        """Build the LangGraph workflow for job search."""
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_profile", self.analyze_profile_node)
        workflow.add_node("search_jobs", self.search_jobs_node)
        workflow.add_node("score_jobs", self.score_jobs_node)
        workflow.add_node("filter_matches", self.filter_matches_node)
        workflow.add_node("generate_proposals", self.generate_proposals_node)
        workflow.add_node("send_notifications", self.send_notifications_node)
        
        # Add edges
        workflow.set_entry_point("analyze_profile")
        workflow.add_edge("analyze_profile", "search_jobs")
        workflow.add_edge("search_jobs", "score_jobs")
        workflow.add_edge("score_jobs", "filter_matches")
        workflow.add_edge("filter_matches", "generate_proposals")
        workflow.add_edge("generate_proposals", "send_notifications")
        workflow.add_edge("send_notifications", END)
        
        return workflow.compile()
    
    async def analyze_profile_node(self, state: AgentState) -> AgentState:
        """Analyze user profile to understand preferences."""
        logger.info(f"Analyzing profile for user {state['user_id']}")
        
        try:
            from backend.agents.tools import analyze_user_profile
            
            result = await analyze_user_profile.ainvoke({"user_id": state["user_id"]})
            
            if result["success"]:
                state["user_profile"] = result["profile"]
                state["messages"].append(f"✓ Profile analyzed: {result['profile']['profession']}")
                
                # Build search query from profile
                state["search_query"] = {
                    "keywords": result["profile"]["skills"][:5],  # Top 5 skills
                    "profession": result["profile"]["profession"],
                    "remote_only": result["profile"]["preferences"]["remote_only"],
                    "limit": 20
                }
            else:
                state["errors"].append(f"Failed to analyze profile: {result.get('error')}")
                
        except Exception as e:
            state["errors"].append(f"Error in profile analysis: {str(e)}")
        
        return state
    
    async def search_jobs_node(self, state: AgentState) -> AgentState:
        """Search for jobs based on profile."""
        logger.info("Searching for jobs")
        
        try:
            from backend.agents.tools import search_jobs
            
            if not state.get("search_query"):
                # Default search if no query built
                state["search_query"] = {
                    "keywords": ["python", "backend"],
                    "remote_only": True,
                    "limit": 20
                }
            
            result = await search_jobs.ainvoke(state["search_query"])
            
            if result["success"]:
                state["raw_jobs"] = result["jobs"]
                state["messages"].append(
                    f"✓ Found {result['total_results']} jobs from {len(result['source_stats'])} sources"
                )
            else:
                state["errors"].append(f"Job search failed: {result.get('error')}")
                
        except Exception as e:
            state["errors"].append(f"Error in job search: {str(e)}")
        
        return state
    
    async def score_jobs_node(self, state: AgentState) -> AgentState:
        """Score all found jobs."""
        logger.info(f"Scoring {len(state.get('raw_jobs', []))} jobs")
        
        try:
            from backend.agents.tools import score_jobs
            
            if state.get("raw_jobs"):
                job_ids = [job["id"] for job in state["raw_jobs"]]
                
                result = await score_jobs.ainvoke({
                    "job_ids": job_ids,
                    "user_id": state["user_id"]
                })
                
                if result["success"]:
                    state["scored_jobs"] = result["scored_jobs"]
                    state["messages"].append(
                        f"✓ Scored {len(result['scored_jobs'])} jobs"
                    )
                else:
                    state["errors"].append(f"Job scoring failed: {result.get('error')}")
            else:
                state["messages"].append("No jobs to score")
                
        except Exception as e:
            state["errors"].append(f"Error in job scoring: {str(e)}")
        
        return state
    
    async def filter_matches_node(self, state: AgentState) -> AgentState:
        """Filter top matches based on scores."""
        logger.info("Filtering top matches")

        min_score = state.get("min_score", 70.0)

        try:
            # Get jobs with score >= min_score
            if state.get("scored_jobs"):
                state["top_matches"] = [
                    job for job in state["scored_jobs"]
                    if job["total_score"] >= min_score
                ][:10]  # Top 10 matches

                state["messages"].append(
                    f"✓ Found {len(state['top_matches'])} high-quality matches (score ≥ {min_score})"
                )
            else:
                state["top_matches"] = []
                state["messages"].append("No matches found")

        except Exception as e:
            state["errors"].append(f"Error filtering matches: {str(e)}")

        return state
    
    async def generate_proposals_node(self, state: AgentState) -> AgentState:
        """Generate proposals for top matches."""
        # Check if proposal generation is enabled
        if not state.get("generate_proposals", True):
            state["messages"].append("Skipping proposal generation (disabled)")
            return state

        max_proposals = state.get("max_proposals", 5)
        logger.info(f"Generating up to {max_proposals} proposals for top matches")

        try:
            from backend.agents.tools import generate_proposal

            state["proposals"] = {}

            # Generate proposals for top N matches
            for job in state.get("top_matches", [])[:max_proposals]:
                result = await generate_proposal.ainvoke({
                    "job_id": job["job_id"],
                    "user_id": state["user_id"],
                    "tone": "professional"
                })

                if result["success"]:
                    state["proposals"][job["job_id"]] = result["proposal"]

            if state["proposals"]:
                state["messages"].append(
                    f"✓ Generated {len(state['proposals'])} personalized proposals"
                )

        except Exception as e:
            state["errors"].append(f"Error generating proposals: {str(e)}")

        return state
    
    async def send_notifications_node(self, state: AgentState) -> AgentState:
        """Send notifications about matches."""
        logger.info("Sending notifications")
        
        try:
            from backend.agents.tools import send_notification
            
            if state.get("top_matches"):
                # Create summary message
                summary = f"Found {len(state['top_matches'])} great job matches for you!\n\n"
                
                for i, job in enumerate(state["top_matches"][:3], 1):
                    summary += f"{i}. {job['title']} at {job['company']} (Score: {job['total_score']:.0f}%)\n"
                
                result = await send_notification.ainvoke({
                    "user_id": state["user_id"],
                    "message": summary,
                    "job_matches": state["top_matches"]
                })
                
                if result["success"]:
                    state["notifications_sent"] = True
                    state["messages"].append("✓ Notifications sent successfully")
                else:
                    state["errors"].append(f"Notification failed: {result.get('error')}")
            else:
                state["messages"].append("No matches to notify about")
                
        except Exception as e:
            state["errors"].append(f"Error sending notifications: {str(e)}")
        
        return state
    
    async def run(
        self,
        user_id: str,
        keywords: Optional[List[str]] = None,
        profession: Optional[str] = None,
        remote_only: bool = True,
        min_score: float = 70.0,
        generate_proposals: bool = True,
        max_proposals: int = 5
    ) -> Dict[str, Any]:
        """
        Run the complete job search workflow for a user.

        Args:
            user_id: User ID to search for
            keywords: Optional custom keywords to add to search
            profession: Optional profession override
            remote_only: Only search for remote jobs
            min_score: Minimum match score threshold
            generate_proposals: Whether to generate proposals for top matches
            max_proposals: Maximum number of proposals to generate

        Returns:
            Dictionary with results and status
        """
        logger.info(f"Starting JobRadar agent for user {user_id}")

        # Initialize state
        initial_state: AgentState = {
            "user_id": user_id,
            "user_profile": None,
            "search_query": None,
            "raw_jobs": [],
            "scored_jobs": [],
            "top_matches": [],
            "proposals": {},
            "notifications_sent": False,
            "messages": [],
            "errors": [],
            # Config
            "min_score": min_score,
            "generate_proposals": generate_proposals,
            "max_proposals": max_proposals
        }

        # Add custom search parameters if provided
        if keywords or profession:
            initial_state["search_query"] = {
                "keywords": keywords or [],
                "profession": profession,
                "remote_only": remote_only,
                "limit": 20
            }

        # Run the workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            # Build top_matches with proposals attached
            top_matches_with_proposals = []
            for match in final_state["top_matches"]:
                match_data = {
                    "job_id": match.get("job_id", ""),
                    "title": match.get("title", ""),
                    "company": match.get("company", ""),
                    "location": match.get("location"),
                    "remote": match.get("remote", False),
                    "score": match.get("total_score", 0),
                    "explanation": match.get("explanation"),
                    "proposal": final_state["proposals"].get(match.get("job_id"))
                }
                top_matches_with_proposals.append(match_data)

            # Prepare response
            response = {
                "success": len(final_state["errors"]) == 0,
                "user_id": user_id,
                "jobs_found": len(final_state.get("raw_jobs", [])),
                "jobs_scored": len(final_state.get("scored_jobs", [])),
                "matches_found": len(final_state["top_matches"]),
                "proposals_generated": len(final_state["proposals"]),
                "notifications_sent": final_state["notifications_sent"],
                "top_matches": top_matches_with_proposals,
                "messages": final_state["messages"],
                "errors": final_state["errors"],
                "timestamp": datetime.utcnow().isoformat()
            }

            # Log summary
            logger.info(
                f"JobRadar completed for user {user_id}: "
                f"{response['matches_found']} matches found, "
                f"{response['proposals_generated']} proposals generated"
            )

            return response

        except Exception as e:
            logger.error(f"JobRadar agent failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": initial_state["messages"],
                "errors": initial_state["errors"] + [str(e)]
            }
    
    async def run_for_all_users(self) -> Dict[str, Any]:
        """
        Run job search for all active users.
        
        Returns:
            Summary of results for all users
        """
        logger.info("Starting batch job search for all users")
        
        try:
            from backend.database import get_async_session
            from backend.models.user import User
            from sqlalchemy import select
            
            results = {
                "total_users": 0,
                "successful_runs": 0,
                "total_matches": 0,
                "total_proposals": 0,
                "user_results": []
            }
            
            async with get_async_session() as db:
                # Get all active users
                user_result = await db.execute(
                    select(User).where(User.is_active == True)
                )
                users = user_result.scalars().all()
                
                results["total_users"] = len(users)
                
                # Run for each user
                for user in users:
                    user_result = await self.run(str(user.id))
                    
                    if user_result["success"]:
                        results["successful_runs"] += 1
                        results["total_matches"] += user_result["matches_found"]
                        results["total_proposals"] += user_result["proposals_generated"]
                    
                    results["user_results"].append({
                        "user_id": str(user.id),
                        "success": user_result["success"],
                        "matches": user_result["matches_found"]
                    })
            
            logger.info(
                f"Batch run complete: {results['successful_runs']}/{results['total_users']} successful, "
                f"{results['total_matches']} total matches"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Batch run failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }