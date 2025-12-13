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
    InterviewPrepRequest,
    InterviewPrepResponse,
    InterviewPrepStatusResponse,
    InterviewPlan,
    ResumeOptimizationRequest,
    ResumeOptimizationResponse,
    ResumeOptimizationStatusResponse,
    ResumeOptimizationResult,
    ResumeSection,
    ATSScore,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for agent run status (in production, use Redis or database)
_agent_runs: Dict[str, AgentRunResponse] = {}
_interview_prep_runs: Dict[str, InterviewPrepResponse] = {}
_resume_optimization_runs: Dict[str, ResumeOptimizationResponse] = {}


async def run_job_radar_agent(
    run_id: str,
    user_id: str,
    request: AgentRunRequest
):
    """Background task to run the Job Radar agent."""
    from backend.agents.job_radar_agent import JobRadarAgent
    from backend.database import async_session

    try:
        # Update status to running
        _agent_runs[run_id].status = AgentStatus.RUNNING
        _agent_runs[run_id].messages.append("Starting Job Radar agent...")

        # Create a new database session for this background task
        async with async_session() as db:
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
        request=request
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
            "proposal_generation",
            "interview_prep",
            "resume_optimization"
        ]
    )


# ============================================================================
# Interview Prep Agent Routes
# ============================================================================

async def run_interview_prep_agent(
    run_id: str,
    user_id: str,
    request: InterviewPrepRequest
):
    """Background task to run the Interview Prep agent."""
    from backend.agents.interview_prep_agent import InterviewPrepAgent
    from backend.database import async_session

    try:
        # Update status to running
        _interview_prep_runs[run_id].status = AgentStatus.RUNNING
        _interview_prep_runs[run_id].messages.append("Starting Interview Prep agent...")

        # Create a new database session for this background task
        async with async_session() as db:
            # Initialize agent
            agent = InterviewPrepAgent(db)
            _interview_prep_runs[run_id].messages.append("Agent initialized")

            # Run the agent
            result = await agent.run(
                user_id=user_id,
                job_id=request.job_id,
                interview_type=request.interview_type,
                difficulty=request.difficulty,
                num_questions=request.num_questions
            )

            # Process results
            if result.get("success"):
                _interview_prep_runs[run_id].session_id = result.get("session_id")
                _interview_prep_runs[run_id].questions_generated = result.get("questions_generated", 0)
                _interview_prep_runs[run_id].prep_tips = result.get("prep_tips", [])
                _interview_prep_runs[run_id].focus_areas = result.get("focus_areas", [])
                _interview_prep_runs[run_id].skill_gaps = result.get("skill_gaps", [])

                # Convert interview plan to response format
                if result.get("interview_plan"):
                    plan_data = result["interview_plan"]
                    _interview_prep_runs[run_id].interview_plan = InterviewPlan(
                        interview_type=plan_data.get("interview_type", "behavioral"),
                        difficulty=plan_data.get("difficulty", "mid"),
                        focus_areas=plan_data.get("focus_areas", []),
                        skill_gaps_to_address=plan_data.get("skill_gaps_to_address", []),
                        target_role=plan_data.get("target_role"),
                        target_company=plan_data.get("target_company"),
                        recommended_frameworks=plan_data.get("recommended_frameworks", []),
                        question_types=plan_data.get("question_types", [])
                    )

                _interview_prep_runs[run_id].status = AgentStatus.COMPLETED
                _interview_prep_runs[run_id].messages.append(
                    f"Completed! Session created with {result.get('questions_generated', 0)} questions"
                )
            else:
                _interview_prep_runs[run_id].status = AgentStatus.FAILED
                error_msg = result.get("error", "Unknown error")
                errors_list = result.get("errors", [])
                if errors_list:
                    _interview_prep_runs[run_id].errors.extend(errors_list)
                else:
                    _interview_prep_runs[run_id].errors.append(error_msg)
                logger.error(f"Interview Prep run {run_id} failed: {error_msg}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Interview Prep run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _interview_prep_runs[run_id].status = AgentStatus.FAILED
        _interview_prep_runs[run_id].errors.append(error_msg)
    finally:
        _interview_prep_runs[run_id].completed_at = datetime.utcnow()


@router.post("/interview/prep", response_model=InterviewPrepResponse)
async def start_interview_prep(
    request: InterviewPrepRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start an Interview Prep agent run.

    The agent will:
    1. Analyze your profile to understand your skills and experience
    2. Analyze the target job (if provided) to identify requirements
    3. Identify skill gaps and focus areas
    4. Create a personalized interview prep plan
    5. Create a practice session with tailored questions
    6. Generate personalized prep tips

    Returns immediately with a run_id. Use /interview/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = InterviewPrepResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Interview Prep run queued"]
    )

    # Store in memory
    _interview_prep_runs[run_id] = run_response

    # Start background task
    background_tasks.add_task(
        run_interview_prep_agent,
        run_id=run_id,
        user_id=str(current_user.id),
        request=request
    )

    logger.info(f"Started Interview Prep run {run_id} for user {current_user.id}")

    return run_response


@router.get("/interview/status/{run_id}", response_model=InterviewPrepStatusResponse)
async def get_interview_prep_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of an Interview Prep run."""
    if run_id not in _interview_prep_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _interview_prep_runs[run_id]

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
        if run.session_id:
            progress = 90.0
            current_step = "Generating tips"
        elif run.interview_plan:
            progress = 70.0
            current_step = "Creating session"
        elif run.skill_gaps:
            progress = 50.0
            current_step = "Creating prep plan"
        elif run.focus_areas:
            progress = 30.0
            current_step = "Identifying gaps"
        else:
            progress = 15.0
            current_step = "Analyzing profile"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return InterviewPrepStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/interview/result/{run_id}", response_model=InterviewPrepResponse)
async def get_interview_prep_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Interview Prep run."""
    if run_id not in _interview_prep_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _interview_prep_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


# ============================================================================
# Resume Optimization Agent Routes
# ============================================================================

async def run_resume_optimization_agent(
    run_id: str,
    user_id: str,
    request: ResumeOptimizationRequest
):
    """Background task to run the Resume Optimization agent."""
    from backend.agents.resume_optimization_agent import ResumeOptimizationAgent

    try:
        # Update status to running
        _resume_optimization_runs[run_id].status = AgentStatus.RUNNING
        _resume_optimization_runs[run_id].messages.append("Starting Resume Optimization agent...")

        # Initialize agent (it manages its own database sessions internally)
        agent = ResumeOptimizationAgent()
        _resume_optimization_runs[run_id].messages.append("Agent initialized")

        # Run the agent
        result = await agent.run(
            user_id=user_id,
            job_id=request.job_id,
            job_description=request.job_description,
            optimization_focus=request.optimization_focus,
            include_cover_letter=request.include_cover_letter,
            preserve_formatting=request.preserve_formatting
        )

        # Process results
        if result is None:
            _resume_optimization_runs[run_id].status = AgentStatus.FAILED
            _resume_optimization_runs[run_id].errors.append("Agent returned no result")
            logger.error(f"Resume Optimization run {run_id} failed: Agent returned None")
            return

        if result.get("success"):
            # Set target job info
            _resume_optimization_runs[run_id].target_job_title = result.get("target_job_title")
            _resume_optimization_runs[run_id].target_company = result.get("target_company")

            # Get the nested result data
            result_data = result.get("result", {})

            # Build optimization result
            optimization_result = ResumeOptimizationResult(
                optimized_sections=[
                    ResumeSection(
                        section_name=section.get("section_name", ""),
                        original_content=section.get("original_content"),
                        optimized_content=section.get("optimized_content", ""),
                        improvement_notes=section.get("improvement_notes", []),
                        keywords_added=section.get("keywords_added", [])
                    )
                    for section in result_data.get("optimized_sections", [])
                ],
                keywords_matched=result_data.get("keywords_matched", []),
                keywords_missing=result_data.get("keywords_missing", []),
                skills_highlighted=result_data.get("skills_highlighted", []),
                improvement_summary=result_data.get("improvement_summary", ""),
                cover_letter=result_data.get("cover_letter")
            )

            # Add ATS scores if available
            if result_data.get("ats_score_before"):
                score_before = result_data["ats_score_before"]
                optimization_result.ats_score_before = ATSScore(
                    overall_score=score_before.get("overall_score", 0),
                    keyword_match=score_before.get("keyword_match", 0),
                    formatting_score=score_before.get("formatting_score", 0),
                    section_completeness=score_before.get("section_completeness", 0),
                    readability_score=score_before.get("readability_score", 0),
                    issues=score_before.get("issues", []),
                    suggestions=score_before.get("suggestions", [])
                )

            if result_data.get("ats_score_after"):
                score_after = result_data["ats_score_after"]
                optimization_result.ats_score_after = ATSScore(
                    overall_score=score_after.get("overall_score", 0),
                    keyword_match=score_after.get("keyword_match", 0),
                    formatting_score=score_after.get("formatting_score", 0),
                    section_completeness=score_after.get("section_completeness", 0),
                    readability_score=score_after.get("readability_score", 0),
                    issues=score_after.get("issues", []),
                    suggestions=score_after.get("suggestions", [])
                )

            _resume_optimization_runs[run_id].result = optimization_result
            _resume_optimization_runs[run_id].status = AgentStatus.COMPLETED

            # Calculate improvement
            score_before = result_data.get("ats_score_before", {}).get("overall_score", 0)
            score_after = result_data.get("ats_score_after", {}).get("overall_score", 0)
            improvement = score_after - score_before

            _resume_optimization_runs[run_id].messages.append(
                f"Completed! ATS score improved from {score_before} to {score_after} (+{improvement} points)"
            )
        else:
            _resume_optimization_runs[run_id].status = AgentStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            errors_list = result.get("errors", [])
            if errors_list:
                _resume_optimization_runs[run_id].errors.extend(errors_list)
            else:
                _resume_optimization_runs[run_id].errors.append(error_msg)
            logger.error(f"Resume Optimization run {run_id} failed: {error_msg}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Resume Optimization run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _resume_optimization_runs[run_id].status = AgentStatus.FAILED
        _resume_optimization_runs[run_id].errors.append(error_msg)
    finally:
        _resume_optimization_runs[run_id].completed_at = datetime.utcnow()


@router.post("/resume/optimize", response_model=ResumeOptimizationResponse)
async def start_resume_optimization(
    request: ResumeOptimizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a Resume Optimization agent run.

    The agent will:
    1. Load and analyze your current resume
    2. Analyze the target job requirements (if provided)
    3. Perform an ATS compatibility audit
    4. Identify keyword gaps and opportunities
    5. Optimize each resume section for maximum impact
    6. Optionally generate a tailored cover letter
    7. Calculate before/after ATS scores

    Returns immediately with a run_id. Use /resume/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = ResumeOptimizationResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Resume Optimization run queued"]
    )

    # Store in memory
    _resume_optimization_runs[run_id] = run_response

    # Start background task using asyncio.create_task to stay in the same event loop
    # This is necessary for async SQLAlchemy to work correctly
    import asyncio
    asyncio.create_task(
        run_resume_optimization_agent(
            run_id=run_id,
            user_id=str(current_user.id),
            request=request
        )
    )

    logger.info(f"Started Resume Optimization run {run_id} for user {current_user.id}")

    return run_response


@router.get("/resume/status/{run_id}", response_model=ResumeOptimizationStatusResponse)
async def get_resume_optimization_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Resume Optimization run."""
    if run_id not in _resume_optimization_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _resume_optimization_runs[run_id]

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
        messages_text = " ".join(run.messages).lower()
        if "cover letter" in messages_text:
            progress = 90.0
            current_step = "Generating cover letter"
        elif "optimiz" in messages_text:
            progress = 70.0
            current_step = "Optimizing sections"
        elif "keyword" in messages_text:
            progress = 50.0
            current_step = "Analyzing keywords"
        elif "ats" in messages_text or "audit" in messages_text:
            progress = 35.0
            current_step = "Performing ATS audit"
        elif "target" in messages_text or "job" in messages_text:
            progress = 20.0
            current_step = "Analyzing target job"
        else:
            progress = 10.0
            current_step = "Loading resume"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return ResumeOptimizationStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/resume/result/{run_id}", response_model=ResumeOptimizationResponse)
async def get_resume_optimization_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Resume Optimization run."""
    if run_id not in _resume_optimization_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _resume_optimization_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run
