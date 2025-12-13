"""Agent API routes - Job Radar and other agentic features."""

import asyncio
import logging
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.dependencies import get_current_user
from backend.models.user import User
from backend.api.schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStatusResponse,
    AgentHealthResponse,
    AgentStatus,
    JobMatchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for agent run status (in production, use Redis or database)
_agent_runs: Dict[str, AgentRunResponse] = {}


async def run_job_radar_agent(
    run_id: str,
    user_id: str,
    request: AgentRunRequest,
    db: AsyncSession
):
    """Background task to run the Job Radar agent."""
    from backend.agents.job_radar_agent import JobRadarAgent

    try:
        # Update status to running
        _agent_runs[run_id].status = AgentStatus.RUNNING
        _agent_runs[run_id].messages.append("Starting Job Radar agent...")

        # Initialize agent
        agent = JobRadarAgent(db)
        _agent_runs[run_id].messages.append("Agent initialized")

        # Run the agent
        result = await agent.run(
            user_id=user_id,
            keywords=request.keywords,
            profession=request.profession,
            remote_only=request.remote_only,
            min_score=request.min_score,
            generate_proposals=request.generate_proposals,
            max_proposals=request.max_proposals
        )

        # Process results
        if result.get("success"):
            _agent_runs[run_id].jobs_found = result.get("jobs_found", 0)
            _agent_runs[run_id].jobs_scored = result.get("jobs_scored", 0)
            _agent_runs[run_id].matches_found = result.get("matches_found", 0)
            _agent_runs[run_id].proposals_generated = result.get("proposals_generated", 0)

            # Convert matches to response format
            for match in result.get("top_matches", []):
                _agent_runs[run_id].top_matches.append(
                    JobMatchResult(
                        job_id=str(match.get("job_id", "")),
                        title=match.get("title", ""),
                        company=match.get("company", ""),
                        location=match.get("location"),
                        remote=match.get("remote", False),
                        score=match.get("score", 0),
                        explanation=match.get("explanation"),
                        proposal=match.get("proposal")
                    )
                )

            _agent_runs[run_id].status = AgentStatus.COMPLETED
            _agent_runs[run_id].messages.append(f"Completed! Found {_agent_runs[run_id].matches_found} matches")
        else:
            _agent_runs[run_id].status = AgentStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            errors_list = result.get("errors", [])
            if errors_list:
                _agent_runs[run_id].errors.extend(errors_list)
            else:
                _agent_runs[run_id].errors.append(error_msg)
            logger.error(f"Agent run {run_id} returned failure: {error_msg}, errors: {errors_list}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Agent run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _agent_runs[run_id].status = AgentStatus.FAILED
        _agent_runs[run_id].errors.append(error_msg)
    finally:
        _agent_runs[run_id].completed_at = datetime.utcnow()


@router.post("/radar/run", response_model=AgentRunResponse)
async def start_job_radar(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a Job Radar agent run.

    The agent will:
    1. Analyze your profile to understand your skills and preferences
    2. Search for relevant jobs across multiple sources
    3. Score and rank jobs based on fit
    4. Generate personalized proposals for top matches

    Returns immediately with a run_id. Use /radar/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = AgentRunResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Job Radar run queued"]
    )

    # Store in memory
    _agent_runs[run_id] = run_response

    # Start background task
    background_tasks.add_task(
        run_job_radar_agent,
        run_id=run_id,
        user_id=str(current_user.id),
        request=request,
        db=db
    )

    logger.info(f"Started Job Radar run {run_id} for user {current_user.id}")

    return run_response


@router.get("/radar/status/{run_id}", response_model=AgentRunStatusResponse)
async def get_radar_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Job Radar run."""
    if run_id not in _agent_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _agent_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    # Calculate progress
    progress = 0.0
    current_step = ""

    if run.status == AgentStatus.PENDING:
        progress = 0.0
        current_step = "Queued"
    elif run.status == AgentStatus.RUNNING:
        # Estimate progress based on messages
        if run.proposals_generated > 0:
            progress = 90.0
            current_step = "Generating proposals"
        elif run.matches_found > 0:
            progress = 70.0
            current_step = "Found matches, scoring"
        elif run.jobs_found > 0:
            progress = 40.0
            current_step = "Scoring jobs"
        else:
            progress = 20.0
            current_step = "Searching for jobs"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return AgentRunStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/radar/result/{run_id}", response_model=AgentRunResponse)
async def get_radar_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Job Radar run."""
    if run_id not in _agent_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _agent_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


@router.get("/health", response_model=AgentHealthResponse)
async def agent_health():
    """Check agent service health and capabilities."""
    from backend.config import settings

    # Check LLM availability
    llm_available = False
    llm_provider = settings.llm_provider

    try:
        if llm_provider == "ollama":
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.ollama_base_url}/api/tags",
                    timeout=5.0
                )
                llm_available = response.status_code == 200
        elif llm_provider == "openai":
            llm_available = bool(settings.openai_api_key)
        elif llm_provider == "anthropic":
            llm_available = bool(settings.anthropic_api_key)
    except Exception as e:
        logger.warning(f"LLM health check failed: {e}")

    return AgentHealthResponse(
        status="healthy" if llm_available else "degraded",
        llm_provider=llm_provider,
        llm_available=llm_available,
        supported_features=[
            "job_radar",
            "profile_analysis",
            "job_scoring",
            "proposal_generation"
        ]
    )
