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
    ApplicationTrackerRequest,
    ApplicationTrackerResponse,
    ApplicationTrackerStatusResponse,
    PortfolioAnalysis,
    StaleApplication,
    Recommendation,
    ActionItem,
    ApplicationStats,
    QuickStatsResponse,
    CoverLetterRequest,
    CoverLetterRegenerateRequest,
    CoverLetterResponse,
    CoverLetterStatusResponse,
    CoverLetterResult,
    SkillAlignment,
    ExperienceMatch,
    SalaryResearchRequest,
    SalaryResearchResponse,
    SalaryResearchStatusResponse,
    SalaryResearchResult,
    SalaryRange,
    MarketData,
    CompensationAnalysis,
    NegotiationStrategy,
    NegotiationScript,
    CommonObjection,
    EquityComponent,
    BonusComponent,
    BenefitsValue,
    SkillGapRequest,
    SkillGapResponse,
    SkillGapStatusResponse,
    SkillGapResult,
    SkillGap,
    LearningResource,
    RecommendedCertification,
    RecommendedProject,
    LearningRoadmap,
    RoadmapPhase,
    RoadmapActivity,
    RoadmapMilestone,
    NetworkIntelligenceRequest,
    NetworkIntelligenceResponse,
    NetworkIntelligenceStatusResponse,
    NetworkIntelligenceResult,
    CompanyInfo,
    CompanyCulture,
    HiringTrends,
    ConnectionType,
    AlumniConnection,
    IndustryConnection,
    RecruiterInsight,
    PotentialContact,
    OutreachTemplate,
    FollowUpStrategy,
    NetworkingEvent,
    OnlineCommunity,
    ContentStrategy,
    WarmIntroductionPath,
    NetworkingActionPlan,
    ImmediateAction,
    WeeklyTask,
    MilestoneTarget,
    NetworkingMetric,
    RiskMitigation,
    # Auto-Apply Agent
    AutoApplyRequest,
    AutoApplyResponse,
    AutoApplyStatusResponse,
    AutoApplyResult,
    JobRequirements,
    FitAssessment,
    SkillsMatch,
    ExperienceMatchAssessment,
    ScreeningQuestion,
    FormFieldData,
    FollowUpPlan,
    FollowUpAction,
    RecruiterOutreach,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for agent run status (in production, use Redis or database)
_agent_runs: Dict[str, AgentRunResponse] = {}
_interview_prep_runs: Dict[str, InterviewPrepResponse] = {}
_resume_optimization_runs: Dict[str, ResumeOptimizationResponse] = {}
_application_tracker_runs: Dict[str, ApplicationTrackerResponse] = {}
_cover_letter_runs: Dict[str, CoverLetterResponse] = {}
_salary_research_runs: Dict[str, SalaryResearchResponse] = {}
_skill_gap_runs: Dict[str, SkillGapResponse] = {}
_network_intelligence_runs: Dict[str, NetworkIntelligenceResponse] = {}
_auto_apply_runs: Dict[str, AutoApplyResponse] = {}


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
            "resume_optimization",
            "application_tracker",
            "cover_letter",
            "salary_research"
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


# ============================================================================
# Application Tracker Agent Routes
# ============================================================================

async def run_application_tracker_agent(
    run_id: str,
    user_id: str,
    request: ApplicationTrackerRequest
):
    """Background task to run the Application Tracker agent."""
    from backend.agents.application_tracker_agent import ApplicationTrackerAgent
    from backend.database import async_session

    try:
        # Update status to running
        _application_tracker_runs[run_id].status = AgentStatus.RUNNING
        _application_tracker_runs[run_id].messages.append("Starting Application Tracker agent...")

        # Create a new database session for this background task
        async with async_session() as db:
            # Initialize agent
            agent = ApplicationTrackerAgent(db)
            _application_tracker_runs[run_id].messages.append("Agent initialized")

            # Run the agent
            result = await agent.run(
                user_id=user_id,
                briefing_type=request.briefing_type
            )

            # Process results
            if result.get("success"):
                _application_tracker_runs[run_id].briefing = result.get("briefing", "")

                # Convert portfolio analysis
                portfolio_data = result.get("portfolio_analysis", {})
                if portfolio_data:
                    _application_tracker_runs[run_id].portfolio_analysis = PortfolioAnalysis(
                        health_score=portfolio_data.get("health_score", 0),
                        total_count=portfolio_data.get("total_count", 0),
                        active_count=portfolio_data.get("active_count", 0),
                        interview_count=portfolio_data.get("interview_count", 0),
                        offer_count=portfolio_data.get("offer_count", 0),
                        response_rate=portfolio_data.get("response_rate", 0),
                        activity_trend=portfolio_data.get("activity_trend", "moderate"),
                        insights=portfolio_data.get("insights", []),
                        status_distribution=portfolio_data.get("status_distribution", {})
                    )

                # Convert stale applications
                for stale in result.get("stale_applications", []):
                    _application_tracker_runs[run_id].stale_applications.append(
                        StaleApplication(
                            application_id=stale.get("application_id", ""),
                            job_title=stale.get("job_title", ""),
                            company=stale.get("company", ""),
                            status=stale.get("status", ""),
                            days_stale=stale.get("days_stale", 0),
                            threshold=stale.get("threshold", 0),
                            urgency=stale.get("urgency", "medium"),
                            reason=stale.get("reason", "")
                        )
                    )

                # Convert recommendations
                for rec in result.get("recommendations", []):
                    _application_tracker_runs[run_id].recommendations.append(
                        Recommendation(
                            type=rec.get("type", "strategy"),
                            title=rec.get("title", ""),
                            description=rec.get("description", ""),
                            priority=rec.get("priority", "medium")
                        )
                    )

                # Convert action items
                for item in result.get("action_items", []):
                    _application_tracker_runs[run_id].action_items.append(
                        ActionItem(
                            type=item.get("type", "follow_up"),
                            priority=item.get("priority", "medium"),
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            application_id=item.get("application_id"),
                            reminder_id=item.get("reminder_id")
                        )
                    )

                # Convert stats
                stats_data = result.get("stats", {})
                if stats_data:
                    _application_tracker_runs[run_id].stats = ApplicationStats(
                        total_applications=stats_data.get("total_applications", 0),
                        active_applications=stats_data.get("active_applications", 0),
                        response_rate=stats_data.get("response_rate", 0),
                        upcoming_reminders=0,  # Not in current stats
                        overdue_reminders=0,
                        by_status=stats_data.get("by_status", {})
                    )

                _application_tracker_runs[run_id].status = AgentStatus.COMPLETED

                # Summary message
                stale_count = len(result.get("stale_applications", []))
                action_count = len(result.get("action_items", []))
                _application_tracker_runs[run_id].messages.append(
                    f"Completed! Found {stale_count} stale applications and {action_count} action items"
                )
            else:
                _application_tracker_runs[run_id].status = AgentStatus.FAILED
                error_msg = result.get("error", "Unknown error")
                _application_tracker_runs[run_id].errors.append(error_msg)
                logger.error(f"Application Tracker run {run_id} failed: {error_msg}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Application Tracker run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _application_tracker_runs[run_id].status = AgentStatus.FAILED
        _application_tracker_runs[run_id].errors.append(error_msg)
    finally:
        _application_tracker_runs[run_id].completed_at = datetime.utcnow()


@router.post("/tracker/briefing", response_model=ApplicationTrackerResponse)
async def start_application_tracker(
    request: ApplicationTrackerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start an Application Tracker agent run.

    The agent will:
    1. Load all your job applications with their timelines and reminders
    2. Analyze your portfolio health and status distribution
    3. Detect stale applications that need follow-up
    4. Generate smart recommendations and action items
    5. Create a personalized briefing (daily, weekly, or full)

    Returns immediately with a run_id. Use /tracker/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = ApplicationTrackerResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Application Tracker run queued"]
    )

    # Store in memory
    _application_tracker_runs[run_id] = run_response

    # Start background task
    background_tasks.add_task(
        run_application_tracker_agent,
        run_id=run_id,
        user_id=str(current_user.id),
        request=request
    )

    logger.info(f"Started Application Tracker run {run_id} for user {current_user.id}")

    return run_response


@router.get("/tracker/status/{run_id}", response_model=ApplicationTrackerStatusResponse)
async def get_application_tracker_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of an Application Tracker run."""
    if run_id not in _application_tracker_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _application_tracker_runs[run_id]

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
        if run.briefing:
            progress = 95.0
            current_step = "Finalizing briefing"
        elif run.action_items:
            progress = 80.0
            current_step = "Generating recommendations"
        elif run.stale_applications:
            progress = 60.0
            current_step = "Generating action items"
        elif run.portfolio_analysis:
            progress = 40.0
            current_step = "Detecting stale applications"
        else:
            progress = 20.0
            current_step = "Loading applications"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return ApplicationTrackerStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/tracker/result/{run_id}", response_model=ApplicationTrackerResponse)
async def get_application_tracker_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Application Tracker run."""
    if run_id not in _application_tracker_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _application_tracker_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


@router.get("/tracker/quick-stats", response_model=QuickStatsResponse)
async def get_quick_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get quick application stats for dashboard display.

    This is a lightweight endpoint that returns basic stats
    without running the full agent workflow.
    """
    from backend.agents.application_tracker_agent import ApplicationTrackerAgent

    try:
        agent = ApplicationTrackerAgent(db)
        result = await agent.get_quick_stats(str(current_user.id))

        return QuickStatsResponse(
            success=result.get("success", False),
            total_applications=result.get("total_applications", 0),
            active_applications=result.get("active_applications", 0),
            response_rate=result.get("response_rate", 0),
            upcoming_reminders=result.get("upcoming_reminders", 0),
            overdue_reminders=result.get("overdue_reminders", 0),
            by_status=result.get("by_status", {}),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        return QuickStatsResponse(
            success=False,
            error=str(e)
        )


# ============================================================================
# Cover Letter Agent Routes
# ============================================================================

async def run_cover_letter_agent(
    run_id: str,
    user_id: str,
    request: CoverLetterRequest
):
    """Background task to run the Cover Letter agent."""
    from backend.agents.cover_letter_agent import CoverLetterAgent
    from backend.database import async_session

    try:
        # Update status to running
        _cover_letter_runs[run_id].status = AgentStatus.RUNNING
        _cover_letter_runs[run_id].messages.append("Starting Cover Letter agent...")

        # Create a new database session for this background task
        async with async_session() as db:
            # Initialize agent
            agent = CoverLetterAgent(db)
            _cover_letter_runs[run_id].messages.append("Agent initialized")

            # Run the agent
            result = await agent.run(
                user_id=user_id,
                job_id=request.job_id,
                job_description=request.job_description,
                style=request.style,
                length=request.length,
                include_salary_expectations=request.include_salary_expectations,
                emphasize_remote=request.emphasize_remote
            )

            # Process results
            if result.get("success"):
                _cover_letter_runs[run_id].target_job_title = result.get("target_job_title")
                _cover_letter_runs[run_id].target_company = result.get("target_company")
                _cover_letter_runs[run_id].style_used = result.get("style")
                _cover_letter_runs[run_id].length_used = result.get("length")

                # Build skill alignment if available
                skill_alignment_data = result.get("skill_alignment", {})
                skill_alignment = None
                if skill_alignment_data:
                    skill_alignment = SkillAlignment(
                        matched_skills=skill_alignment_data.get("matched_skills", []),
                        partial_matches=skill_alignment_data.get("partial_matches", []),
                        missing_skills=skill_alignment_data.get("missing_skills", []),
                        alignment_score=skill_alignment_data.get("alignment_score", 0.0),
                        summary=skill_alignment_data.get("summary", "")
                    )

                # Build experience matches
                experience_matches = []
                for match in result.get("experience_matches", []):
                    experience_matches.append(
                        ExperienceMatch(
                            experience_title=match.get("experience_title", ""),
                            relevance_score=match.get("relevance_score", 0.0),
                            matched_keywords=match.get("matched_keywords", []),
                            highlight_points=match.get("highlight_points", [])
                        )
                    )

                # Build the result
                _cover_letter_runs[run_id].result = CoverLetterResult(
                    cover_letter=result.get("cover_letter", ""),
                    ats_score=result.get("ats_score", 0),
                    keywords_used=result.get("keywords_used", []),
                    keywords_missing=result.get("keywords_missing", []),
                    skill_alignment=skill_alignment,
                    experience_matches=experience_matches,
                    suggestions=result.get("suggestions", [])
                )

                _cover_letter_runs[run_id].status = AgentStatus.COMPLETED
                ats_score = result.get("ats_score", 0)
                _cover_letter_runs[run_id].messages.append(
                    f"Completed! Cover letter generated with ATS score: {ats_score}"
                )
            else:
                _cover_letter_runs[run_id].status = AgentStatus.FAILED
                error_msg = result.get("error", "Unknown error")
                errors_list = result.get("errors", [])
                if errors_list:
                    _cover_letter_runs[run_id].errors.extend(errors_list)
                else:
                    _cover_letter_runs[run_id].errors.append(error_msg)
                logger.error(f"Cover Letter run {run_id} failed: {error_msg}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Cover Letter run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _cover_letter_runs[run_id].status = AgentStatus.FAILED
        _cover_letter_runs[run_id].errors.append(error_msg)
    finally:
        _cover_letter_runs[run_id].completed_at = datetime.utcnow()


@router.post("/cover-letter/generate", response_model=CoverLetterResponse)
async def start_cover_letter_generation(
    request: CoverLetterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a Cover Letter generation run.

    The agent will:
    1. Load your resume and profile data
    2. Analyze skill alignment with the target job
    3. Extract relevant keywords from the job description
    4. Match your experience to job requirements
    5. Generate a personalized cover letter
    6. Calculate ATS compatibility score
    7. Provide improvement suggestions

    Returns immediately with a run_id. Use /cover-letter/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = CoverLetterResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Cover Letter generation queued"]
    )

    # Store in memory
    _cover_letter_runs[run_id] = run_response

    # Start background task
    background_tasks.add_task(
        run_cover_letter_agent,
        run_id=run_id,
        user_id=str(current_user.id),
        request=request
    )

    logger.info(f"Started Cover Letter run {run_id} for user {current_user.id}")

    return run_response


@router.get("/cover-letter/status/{run_id}", response_model=CoverLetterStatusResponse)
async def get_cover_letter_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Cover Letter generation run."""
    if run_id not in _cover_letter_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _cover_letter_runs[run_id]

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
        messages_text = " ".join(run.messages).lower()
        if "suggestion" in messages_text:
            progress = 95.0
            current_step = "Generating suggestions"
        elif "ats" in messages_text or "score" in messages_text:
            progress = 85.0
            current_step = "Calculating ATS score"
        elif "generat" in messages_text and "letter" in messages_text:
            progress = 70.0
            current_step = "Generating cover letter"
        elif "experience" in messages_text or "match" in messages_text:
            progress = 55.0
            current_step = "Matching experience"
        elif "keyword" in messages_text:
            progress = 40.0
            current_step = "Extracting keywords"
        elif "align" in messages_text or "skill" in messages_text:
            progress = 25.0
            current_step = "Analyzing skill alignment"
        else:
            progress = 10.0
            current_step = "Loading data"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return CoverLetterStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/cover-letter/result/{run_id}", response_model=CoverLetterResponse)
async def get_cover_letter_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Cover Letter generation run."""
    if run_id not in _cover_letter_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _cover_letter_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


@router.post("/cover-letter/regenerate", response_model=CoverLetterResponse)
async def regenerate_cover_letter(
    request: CoverLetterRegenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerate a cover letter with feedback.

    Provide the original cover letter and feedback to get an improved version.
    Useful for iterative refinement based on user preferences.
    """
    from backend.agents.cover_letter_agent import CoverLetterAgent

    run_id = str(uuid4())

    # Create initial response
    run_response = CoverLetterResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Cover Letter regeneration queued"]
    )

    # Store in memory
    _cover_letter_runs[run_id] = run_response

    async def run_regeneration():
        from backend.database import async_session

        try:
            _cover_letter_runs[run_id].status = AgentStatus.RUNNING
            _cover_letter_runs[run_id].messages.append("Regenerating with feedback...")

            async with async_session() as session:
                agent = CoverLetterAgent(session)

                result = await agent.regenerate_with_feedback(
                    user_id=str(current_user.id),
                    original_letter=request.original_letter,
                    feedback=request.feedback,
                    job_id=request.job_id,
                    job_description=request.job_description
                )

                if result.get("success"):
                    _cover_letter_runs[run_id].result = CoverLetterResult(
                        cover_letter=result.get("cover_letter", ""),
                        ats_score=result.get("ats_score", 0),
                        keywords_used=result.get("keywords_used", []),
                        keywords_missing=result.get("keywords_missing", []),
                        suggestions=result.get("suggestions", [])
                    )
                    _cover_letter_runs[run_id].status = AgentStatus.COMPLETED
                    _cover_letter_runs[run_id].messages.append("Regeneration complete!")
                else:
                    _cover_letter_runs[run_id].status = AgentStatus.FAILED
                    _cover_letter_runs[run_id].errors.append(
                        result.get("error", "Regeneration failed")
                    )

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"Cover Letter regeneration {run_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            _cover_letter_runs[run_id].status = AgentStatus.FAILED
            _cover_letter_runs[run_id].errors.append(error_msg)
        finally:
            _cover_letter_runs[run_id].completed_at = datetime.utcnow()

    # Start background task
    background_tasks.add_task(run_regeneration)

    logger.info(f"Started Cover Letter regeneration {run_id} for user {current_user.id}")

    return run_response


# ============================================================================
# Salary Research & Negotiation Agent Routes
# ============================================================================

async def run_salary_research_agent(
    run_id: str,
    user_id: str,
    request: SalaryResearchRequest
):
    """Background task to run the Salary Research agent."""
    from backend.agents.salary_agent import SalaryAgent

    try:
        # Update status to running
        _salary_research_runs[run_id].status = AgentStatus.RUNNING
        _salary_research_runs[run_id].messages.append("Starting Salary Research agent...")

        # Initialize agent (manages its own sessions)
        agent = SalaryAgent()
        await agent.initialize()
        _salary_research_runs[run_id].messages.append("Agent initialized")

        # Run the agent
        result = await agent.run(
            user_id=user_id,
            job_title=request.job_title,
            location=request.location,
            years_experience=request.years_experience,
            current_salary=request.current_salary,
            target_salary=request.target_salary,
            company_name=request.company_name,
            job_level=request.job_level,
            include_negotiation_scripts=request.include_negotiation_scripts
        )

        # Process results - agent returns "status": "completed" or "failed"
        if result.get("status") == "completed":
            # Extract job details for the result
            job_title = result.get("job_title", "Unknown Position")
            location = result.get("location", "Unknown Location")

            # Build market data
            market_data_raw = result.get("market_data", {})
            market_data = None
            base_salary_range = None
            if market_data_raw:
                salary_range_raw = market_data_raw.get("salary_range", {}) or market_data_raw.get("base_salary", {})
                base_salary_range = SalaryRange(
                    min=salary_range_raw.get("min", salary_range_raw.get("min_salary", 0)),
                    max=salary_range_raw.get("max", salary_range_raw.get("max_salary", 0)),
                    median=salary_range_raw.get("median", salary_range_raw.get("median_salary", 0)),
                    p25=salary_range_raw.get("p25", salary_range_raw.get("percentile_25", 0)),
                    p75=salary_range_raw.get("p75", salary_range_raw.get("percentile_75", 0))
                )
                market_data = MarketData(
                    base_salary=base_salary_range,
                    typical_bonus_percent=market_data_raw.get("typical_bonus_percent", 0),
                    typical_equity_value=market_data_raw.get("typical_equity_value", 0),
                    market_demand=market_data_raw.get("market_demand", market_data_raw.get("demand_level", "medium")),
                    salary_trend=market_data_raw.get("salary_trend", market_data_raw.get("market_trend", "stable")),
                    key_factors=market_data_raw.get("key_factors", []),
                    data_sources=market_data_raw.get("data_sources", [])
                )

            # Build compensation analysis
            comp_raw = result.get("compensation_analysis", {})
            compensation_analysis = None
            if comp_raw:
                equity_raw = comp_raw.get("equity_component", {})
                equity_comp = None
                if equity_raw:
                    equity_comp = EquityComponent(
                        typical_grant_value=equity_raw.get("typical_grant_value", 0),
                        annual_value=equity_raw.get("annual_value", 0),
                        vesting_schedule=equity_raw.get("vesting_schedule", "4-year with 1-year cliff"),
                        type=equity_raw.get("type", "RSU")
                    )

                bonus_raw = comp_raw.get("bonus_component", {})
                bonus_comp = None
                if bonus_raw:
                    bonus_comp = BonusComponent(
                        target_percent=bonus_raw.get("target_percent", 0),
                        typical_range=bonus_raw.get("typical_range", ""),
                        timing=bonus_raw.get("timing", "Annual")
                    )

                benefits_raw = comp_raw.get("benefits_value", {})
                benefits_val = None
                if benefits_raw:
                    benefits_val = BenefitsValue(
                        health_insurance_value=benefits_raw.get("health_insurance_value", 0),
                        retirement_match=benefits_raw.get("retirement_match", 0),
                        pto_value=benefits_raw.get("pto_value", 0),
                        other_benefits=benefits_raw.get("other_benefits", [])
                    )

                compensation_analysis = CompensationAnalysis(
                    base_salary_weight=comp_raw.get("base_salary_weight", 70),
                    equity_component=equity_comp,
                    bonus_component=bonus_comp,
                    benefits_value=benefits_val,
                    additional_perks=comp_raw.get("additional_perks", []),
                    remote_premium_or_discount=comp_raw.get("remote_premium_or_discount", 0),
                    negotiable_components=comp_raw.get("negotiable_components", [])
                )

            # Build negotiation strategy
            strategy_raw = result.get("negotiation_strategy", {})
            negotiation_strategy = None
            if strategy_raw:
                # Build common objections list
                common_objections = []
                for obj in strategy_raw.get("potential_objections", strategy_raw.get("common_objections", [])):
                    if isinstance(obj, dict):
                        common_objections.append(CommonObjection(
                            objection=obj.get("objection", ""),
                            response=obj.get("response", "")
                        ))
                    elif isinstance(obj, str):
                        common_objections.append(CommonObjection(objection=obj, response=""))

                negotiation_strategy = NegotiationStrategy(
                    recommended_ask=float(strategy_raw.get("recommended_ask", 0)),
                    walk_away_point=float(strategy_raw.get("walk_away_point", 0)),
                    anchor_high_rationale=strategy_raw.get("anchor_high_rationale", strategy_raw.get("recommended_approach", "")),
                    timing_advice=strategy_raw.get("timing_advice", ""),
                    opening_approach=strategy_raw.get("opening_approach", strategy_raw.get("opening_position", "")),
                    key_talking_points=strategy_raw.get("key_talking_points", strategy_raw.get("key_leverage_points", [])),
                    common_objections=common_objections,
                    alternatives_to_negotiate=strategy_raw.get("alternatives_to_negotiate", strategy_raw.get("alternative_benefits", [])),
                    risk_level=strategy_raw.get("risk_level", strategy_raw.get("confidence_level", "medium")),
                    confidence_score=int(strategy_raw.get("confidence_score", 50))
                )

            # Build negotiation scripts
            scripts = []
            for script_raw in result.get("negotiation_scripts", []):
                scripts.append(
                    NegotiationScript(
                        scenario=script_raw.get("scenario", ""),
                        script=script_raw.get("script", ""),
                        tone=script_raw.get("tone", "professional")
                    )
                )

            # Build salary range for result (use base_salary_range if available)
            result_salary_range = base_salary_range if base_salary_range else SalaryRange(
                min_salary=0, max_salary=0, median_salary=0, currency="USD"
            )

            # Build the result with required fields
            _salary_research_runs[run_id].result = SalaryResearchResult(
                job_title=job_title,
                location=location,
                salary_range=result_salary_range,
                market_data=market_data,
                compensation_analysis=compensation_analysis,
                total_comp_estimate=result.get("total_comp_estimate", 0),
                location_adjustment=result.get("location_adjustment", 1.0),
                experience_adjustment=result.get("experience_adjustment", 1.0),
                negotiation_leverage=result.get("negotiation_leverage", result.get("key_insights", [])),
                negotiation_strategy=negotiation_strategy,
                negotiation_scripts=scripts,
                counter_offer_template=result.get("counter_offer_template", "")
            )

            _salary_research_runs[run_id].status = AgentStatus.COMPLETED
            if base_salary_range and base_salary_range.median:
                median = base_salary_range.median
                _salary_research_runs[run_id].messages.append(
                    f"Completed! Market median: ${median:,.0f}"
                )
            else:
                _salary_research_runs[run_id].messages.append("Completed!")
        else:
            _salary_research_runs[run_id].status = AgentStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            errors_list = result.get("errors", [])
            if errors_list:
                _salary_research_runs[run_id].errors.extend(errors_list)
            else:
                _salary_research_runs[run_id].errors.append(error_msg)
            logger.error(f"Salary Research run {run_id} failed: {error_msg}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Salary Research run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _salary_research_runs[run_id].status = AgentStatus.FAILED
        _salary_research_runs[run_id].errors.append(error_msg)
    finally:
        _salary_research_runs[run_id].completed_at = datetime.utcnow()


@router.post("/salary/research", response_model=SalaryResearchResponse)
async def start_salary_research(
    request: SalaryResearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a Salary Research & Negotiation agent run.

    The agent will:
    1. Load your profile to understand your background and experience
    2. Research market salary data for your target role and location
    3. Analyze total compensation (base, equity, bonus, benefits)
    4. Adjust for location cost-of-living and experience level
    5. Build a personalized negotiation strategy
    6. Generate scripts for common negotiation scenarios

    Returns immediately with a run_id. Use /salary/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = SalaryResearchResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Salary Research run queued"]
    )

    # Store in memory
    _salary_research_runs[run_id] = run_response

    # Start background task
    background_tasks.add_task(
        run_salary_research_agent,
        run_id=run_id,
        user_id=str(current_user.id),
        request=request
    )

    logger.info(f"Started Salary Research run {run_id} for user {current_user.id}")

    return run_response


@router.get("/salary/status/{run_id}", response_model=SalaryResearchStatusResponse)
async def get_salary_research_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Salary Research run."""
    if run_id not in _salary_research_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _salary_research_runs[run_id]

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
        messages_text = " ".join(run.messages).lower()
        if "script" in messages_text:
            progress = 95.0
            current_step = "Generating negotiation scripts"
        elif "strateg" in messages_text:
            progress = 80.0
            current_step = "Building negotiation strategy"
        elif "adjust" in messages_text:
            progress = 65.0
            current_step = "Applying location/experience adjustments"
        elif "compensation" in messages_text or "analyz" in messages_text:
            progress = 50.0
            current_step = "Analyzing compensation"
        elif "market" in messages_text or "research" in messages_text:
            progress = 35.0
            current_step = "Researching market rates"
        elif "load" in messages_text or "profile" in messages_text:
            progress = 15.0
            current_step = "Loading profile data"
        else:
            progress = 10.0
            current_step = "Initializing"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return SalaryResearchStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/salary/result/{run_id}", response_model=SalaryResearchResponse)
async def get_salary_research_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Salary Research run."""
    if run_id not in _salary_research_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _salary_research_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


# ============================================================================
# Skill Gap & Career Development Agent Routes
# ============================================================================

async def run_skill_gap_agent(
    run_id: str,
    user_id: str,
    request: SkillGapRequest
):
    """Background task to run the Skill Gap agent."""
    from backend.agents.skill_gap_agent import SkillGapAgent

    try:
        # Update status to running
        _skill_gap_runs[run_id].status = AgentStatus.RUNNING
        _skill_gap_runs[run_id].messages.append("Starting Skill Gap analysis...")

        # Initialize agent (manages its own sessions)
        agent = SkillGapAgent()
        await agent.initialize()
        _skill_gap_runs[run_id].messages.append("Agent initialized")

        # Run the agent
        result = await agent.run(
            run_id=run_id,
            user_id=user_id,
            target_job_title=request.target_job_title,
            target_job_description=request.target_job_description,
            target_industry=request.target_industry,
            target_company=request.target_company,
            timeframe_months=request.timeframe_months,
            learning_hours_per_week=request.learning_hours_per_week,
            include_certifications=request.include_certifications,
            include_projects=request.include_projects,
            focus_area=request.focus_area
        )

        # Process results
        if result.get("status") == "completed":
            # Build skill gaps list
            skill_gaps = []
            for gap_raw in result.get("skill_gaps", []):
                skill_gaps.append(SkillGap(
                    skill=gap_raw.get("skill", ""),
                    gap_level=gap_raw.get("gap_level", "not_present"),
                    priority=gap_raw.get("priority", "medium"),
                    category=gap_raw.get("category", "technical"),
                    learning_effort=gap_raw.get("learning_effort", "weeks"),
                    prerequisite_skills=gap_raw.get("prerequisite_skills", [])
                ))

            # Build learning resources list
            learning_resources = []
            for res_raw in result.get("learning_resources", []):
                learning_resources.append(LearningResource(
                    skill=res_raw.get("skill", ""),
                    name=res_raw.get("name", ""),
                    type=res_raw.get("type", "online_course"),
                    provider=res_raw.get("provider", ""),
                    url=res_raw.get("url"),
                    duration_hours=int(res_raw.get("duration_hours", 0)),
                    cost=res_raw.get("cost", "free"),
                    difficulty=res_raw.get("difficulty", "intermediate"),
                    rating=float(res_raw.get("rating", 0)),
                    key_topics=res_raw.get("key_topics", [])
                ))

            # Build certifications list
            recommended_certifications = []
            for cert_raw in result.get("recommended_certifications", []):
                recommended_certifications.append(RecommendedCertification(
                    name=cert_raw.get("name", ""),
                    provider=cert_raw.get("provider", ""),
                    skill=cert_raw.get("skill", ""),
                    cost_range=cert_raw.get("cost_range", ""),
                    prep_time_months=int(cert_raw.get("prep_time_months", 1)),
                    career_value=cert_raw.get("career_value", "medium"),
                    prerequisites=cert_raw.get("prerequisites", [])
                ))

            # Build projects list
            recommended_projects = []
            for proj_raw in result.get("recommended_projects", []):
                recommended_projects.append(RecommendedProject(
                    title=proj_raw.get("title", ""),
                    description=proj_raw.get("description", ""),
                    skills_practiced=proj_raw.get("skills_practiced", []),
                    difficulty=proj_raw.get("difficulty", "intermediate"),
                    estimated_hours=int(proj_raw.get("estimated_hours", 0)),
                    portfolio_value=proj_raw.get("portfolio_value", "medium")
                ))

            # Build learning roadmap
            roadmap_raw = result.get("learning_roadmap", {})
            learning_roadmap = None
            if roadmap_raw:
                phases = []
                for phase_raw in roadmap_raw.get("phases", []):
                    activities = []
                    for act_raw in phase_raw.get("activities", []):
                        activities.append(RoadmapActivity(
                            type=act_raw.get("type", "course"),
                            name=act_raw.get("name", ""),
                            hours_per_week=int(act_raw.get("hours_per_week", 0)),
                            description=act_raw.get("description", "")
                        ))
                    phases.append(RoadmapPhase(
                        phase_number=int(phase_raw.get("phase_number", 1)),
                        name=phase_raw.get("name", ""),
                        duration_weeks=int(phase_raw.get("duration_weeks", 4)),
                        focus_skills=phase_raw.get("focus_skills", []),
                        activities=activities,
                        milestones=phase_raw.get("milestones", []),
                        success_metrics=phase_raw.get("success_metrics", [])
                    ))

                key_milestones = []
                for ms_raw in roadmap_raw.get("key_milestones", []):
                    key_milestones.append(RoadmapMilestone(
                        month=int(ms_raw.get("month", 1)),
                        milestone=ms_raw.get("milestone", ""),
                        skills_acquired=ms_raw.get("skills_acquired", [])
                    ))

                learning_roadmap = LearningRoadmap(
                    total_duration_months=int(roadmap_raw.get("total_duration_months", 6)),
                    phases=phases,
                    weekly_schedule_template=roadmap_raw.get("weekly_schedule_template", {}),
                    key_milestones=key_milestones,
                    job_ready_indicators=roadmap_raw.get("job_ready_indicators", [])
                )

            # Build the result
            _skill_gap_runs[run_id].result = SkillGapResult(
                target_job_title=result.get("target_job_title", request.target_job_title),
                target_industry=result.get("target_industry", request.target_industry),
                current_skills=result.get("current_skills", []),
                skill_gaps=skill_gaps,
                transferable_skills=result.get("transferable_skills", []),
                skill_overlap_percent=float(result.get("skill_overlap_percent", 0)),
                market_demand=result.get("market_demand", {}),
                salary_impact=result.get("salary_impact", {}),
                learning_resources=learning_resources,
                recommended_certifications=recommended_certifications,
                recommended_projects=recommended_projects,
                learning_roadmap=learning_roadmap,
                quick_wins=result.get("quick_wins", []),
                long_term_investments=result.get("long_term_investments", [])
            )

            _skill_gap_runs[run_id].status = AgentStatus.COMPLETED
            overlap = result.get("skill_overlap_percent", 0)
            gap_count = len(skill_gaps)
            _skill_gap_runs[run_id].messages.append(
                f"Completed! {overlap:.0f}% skill overlap, {gap_count} gaps identified"
            )
        else:
            _skill_gap_runs[run_id].status = AgentStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            errors_list = result.get("errors", [])
            if errors_list:
                _skill_gap_runs[run_id].errors.extend(errors_list)
            else:
                _skill_gap_runs[run_id].errors.append(error_msg)
            logger.error(f"Skill Gap run {run_id} failed: {error_msg}")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Skill Gap run {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        _skill_gap_runs[run_id].status = AgentStatus.FAILED
        _skill_gap_runs[run_id].errors.append(error_msg)
    finally:
        _skill_gap_runs[run_id].completed_at = datetime.utcnow()


@router.post("/skill-gap/analyze", response_model=SkillGapResponse)
async def start_skill_gap_analysis(
    request: SkillGapRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a Skill Gap Analysis agent run.

    The agent will:
    1. Load your profile and current skills from your resume
    2. Analyze requirements for your target job
    3. Identify skill gaps with priority levels
    4. Research market demand for each skill
    5. Recommend learning resources (courses, certifications, projects)
    6. Build a personalized learning roadmap

    Returns immediately with a run_id. Use /skill-gap/status/{run_id} to check progress.
    """
    run_id = str(uuid4())

    # Create initial response
    run_response = SkillGapResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=["Skill Gap analysis queued"]
    )

    # Store in memory
    _skill_gap_runs[run_id] = run_response

    # Start background task
    background_tasks.add_task(
        run_skill_gap_agent,
        run_id=run_id,
        user_id=str(current_user.id),
        request=request
    )

    logger.info(f"Started Skill Gap run {run_id} for user {current_user.id}")

    return run_response


@router.get("/skill-gap/status/{run_id}", response_model=SkillGapStatusResponse)
async def get_skill_gap_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Skill Gap analysis run."""
    if run_id not in _skill_gap_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _skill_gap_runs[run_id]

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
        messages_text = " ".join(run.messages).lower()
        if "roadmap" in messages_text:
            progress = 90.0
            current_step = "Building learning roadmap"
        elif "resource" in messages_text or "recommend" in messages_text:
            progress = 75.0
            current_step = "Finding learning resources"
        elif "market" in messages_text or "demand" in messages_text:
            progress = 60.0
            current_step = "Researching market demand"
        elif "gap" in messages_text:
            progress = 45.0
            current_step = "Identifying skill gaps"
        elif "target" in messages_text or "requirement" in messages_text:
            progress = 30.0
            current_step = "Analyzing target job requirements"
        elif "load" in messages_text or "profile" in messages_text:
            progress = 15.0
            current_step = "Loading profile data"
        else:
            progress = 10.0
            current_step = "Initializing"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return SkillGapStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/skill-gap/result/{run_id}", response_model=SkillGapResponse)
async def get_skill_gap_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Skill Gap analysis run."""
    if run_id not in _skill_gap_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _skill_gap_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


# =============================================================================
# Network Intelligence Agent Endpoints
# =============================================================================


async def run_network_intelligence_agent(
    run_id: str,
    user_id: str,
    request: NetworkIntelligenceRequest
):
    """Background task to run the Network Intelligence agent."""
    from backend.agents.network_intelligence_agent import NetworkIntelligenceAgent

    try:
        _network_intelligence_runs[run_id].status = AgentStatus.RUNNING
        _network_intelligence_runs[run_id].messages.append("Starting Network Intelligence analysis...")

        agent = NetworkIntelligenceAgent()
        _network_intelligence_runs[run_id].messages.append("Agent initialized")

        result = await agent.run(
            user_id=user_id,
            target_company=request.target_company,
            target_role=request.target_role,
            target_industry=request.target_industry,
            networking_goals=request.networking_goals
        )

        # Build company info
        company_info_data = result.get("company_info", {})
        company_info = CompanyInfo(
            size=company_info_data.get("size", ""),
            industry_focus=company_info_data.get("industry_focus", ""),
            key_departments=company_info_data.get("key_departments", []),
            headquarters=company_info_data.get("headquarters", ""),
            remote_culture=company_info_data.get("remote_culture", ""),
            growth_stage=company_info_data.get("growth_stage", ""),
            recent_news=company_info_data.get("recent_news", [])
        )

        # Build company culture
        culture_data = result.get("company_culture", {})
        company_culture = CompanyCulture(
            values=culture_data.get("values", []),
            work_style=culture_data.get("work_style", ""),
            employee_reviews_themes=culture_data.get("employee_reviews_themes", []),
            innovation_focus=culture_data.get("innovation_focus", ""),
            diversity_initiatives=culture_data.get("diversity_initiatives", [])
        )

        # Build hiring trends
        hiring_data = result.get("hiring_trends", {})
        hiring_trends = HiringTrends(
            current_openings_estimate=hiring_data.get("current_openings_estimate", ""),
            hot_skills=hiring_data.get("hot_skills", []),
            typical_hiring_process=hiring_data.get("typical_hiring_process", ""),
            interview_style=hiring_data.get("interview_style", ""),
            growth_areas=hiring_data.get("growth_areas", [])
        )

        # Build connection types
        connection_types = [
            ConnectionType(
                type=ct.get("type", ""),
                priority=ct.get("priority", "medium"),
                rationale=ct.get("rationale", ""),
                where_to_find=ct.get("where_to_find", []),
                approach_style=ct.get("approach_style", ""),
                expected_value=ct.get("expected_value", "")
            ) for ct in result.get("connection_types", [])
        ]

        # Build alumni connections
        alumni_connections = [
            AlumniConnection(
                school_or_company=ac.get("school_or_company", ""),
                connection_strength=ac.get("connection_strength", "medium"),
                outreach_angle=ac.get("outreach_angle", ""),
                suggested_platforms=ac.get("suggested_platforms", [])
            ) for ac in result.get("alumni_connections", [])
        ]

        # Build industry connections
        industry_connections = [
            IndustryConnection(
                connection_type=ic.get("connection_type", ""),
                relevance=ic.get("relevance", ""),
                how_to_connect=ic.get("how_to_connect", ""),
                common_ground=ic.get("common_ground", [])
            ) for ic in result.get("industry_connections", [])
        ]

        # Build recruiter insights
        recruiter_insights = [
            RecruiterInsight(
                recruiter_type=ri.get("recruiter_type", ""),
                how_to_find=ri.get("how_to_find", ""),
                approach_timing=ri.get("approach_timing", ""),
                what_they_value=ri.get("what_they_value", "")
            ) for ri in result.get("recruiter_insights", [])
        ]

        # Build potential contacts
        potential_contacts = [
            PotentialContact(
                role_type=pc.get("role_type", ""),
                department=pc.get("department", ""),
                seniority=pc.get("seniority", ""),
                value_proposition=pc.get("value_proposition", ""),
                ask=pc.get("ask", ""),
                approach_platform=pc.get("approach_platform", "")
            ) for pc in result.get("potential_contacts", [])
        ]

        # Build outreach templates
        outreach_templates = [
            OutreachTemplate(
                scenario=ot.get("scenario", ""),
                target_role=ot.get("target_role", ""),
                platform=ot.get("platform", ""),
                subject_line=ot.get("subject_line", ""),
                message=ot.get("message", ""),
                call_to_action=ot.get("call_to_action", ""),
                tone=ot.get("tone", ""),
                length=ot.get("length", ""),
                personalization_tips=ot.get("personalization_tips", [])
            ) for ot in result.get("outreach_templates", [])
        ]

        # Build follow-up strategies
        follow_up_strategies = [
            FollowUpStrategy(
                scenario=fs.get("scenario", ""),
                timing=fs.get("timing", ""),
                approach=fs.get("approach", ""),
                message_template=fs.get("message_template", ""),
                persistence_limit=fs.get("persistence_limit", "")
            ) for fs in result.get("follow_up_strategies", [])
        ]

        # Build networking events
        networking_events = [
            NetworkingEvent(
                event_type=ne.get("event_type", ""),
                name=ne.get("name", ""),
                frequency=ne.get("frequency", ""),
                relevance=ne.get("relevance", ""),
                how_to_maximize=ne.get("how_to_maximize", ""),
                likely_attendees=ne.get("likely_attendees", []),
                cost=ne.get("cost", ""),
                location_type=ne.get("location_type", "")
            ) for ne in result.get("networking_events", [])
        ]

        # Build online communities
        online_communities = [
            OnlineCommunity(
                platform=oc.get("platform", ""),
                community_name=oc.get("community_name", ""),
                activity_level=oc.get("activity_level", ""),
                member_profile=oc.get("member_profile", ""),
                engagement_strategy=oc.get("engagement_strategy", ""),
                connection_potential=oc.get("connection_potential", "")
            ) for oc in result.get("online_communities", [])
        ]

        # Build content strategy
        cs_data = result.get("content_strategy", {})
        content_strategy = ContentStrategy(
            platforms=cs_data.get("platforms", []),
            content_types=cs_data.get("content_types", []),
            topics=cs_data.get("topics", []),
            posting_frequency=cs_data.get("posting_frequency", ""),
            engagement_tactics=cs_data.get("engagement_tactics", []),
            hashtags_or_keywords=cs_data.get("hashtags_or_keywords", [])
        )

        # Build warm introduction paths
        warm_introduction_paths = [
            WarmIntroductionPath(
                path=wip.get("path", ""),
                starting_point=wip.get("starting_point", ""),
                intermediate_steps=wip.get("intermediate_steps", []),
                success_likelihood=wip.get("success_likelihood", ""),
                time_estimate=wip.get("time_estimate", "")
            ) for wip in result.get("warm_introduction_paths", [])
        ]

        # Build action plan
        ap_data = result.get("action_plan", {})
        action_plan = NetworkingActionPlan(
            immediate_actions=[
                ImmediateAction(
                    action=ia.get("action", ""),
                    priority=ia.get("priority", ""),
                    time_required=ia.get("time_required", ""),
                    expected_outcome=ia.get("expected_outcome", ""),
                    resources_needed=ia.get("resources_needed", [])
                ) for ia in ap_data.get("immediate_actions", [])
            ],
            weekly_tasks=[
                WeeklyTask(
                    task=wt.get("task", ""),
                    frequency=wt.get("frequency", ""),
                    platform=wt.get("platform", ""),
                    goal=wt.get("goal", "")
                ) for wt in ap_data.get("weekly_tasks", [])
            ],
            milestone_targets=[
                MilestoneTarget(
                    milestone=mt.get("milestone", ""),
                    timeframe=mt.get("timeframe", ""),
                    success_criteria=mt.get("success_criteria", ""),
                    dependencies=mt.get("dependencies", [])
                ) for mt in ap_data.get("milestone_targets", [])
            ],
            metrics_to_track=[
                NetworkingMetric(
                    metric=nm.get("metric", ""),
                    target=nm.get("target", ""),
                    tracking_method=nm.get("tracking_method", "")
                ) for nm in ap_data.get("metrics_to_track", [])
            ],
            risk_mitigation=[
                RiskMitigation(
                    risk=rm.get("risk", ""),
                    mitigation=rm.get("mitigation", "")
                ) for rm in ap_data.get("risk_mitigation", [])
            ]
        )

        # Build final result
        network_result = NetworkIntelligenceResult(
            target_company=result.get("target_company", request.target_company),
            target_role=result.get("target_role"),
            target_industry=result.get("target_industry", request.target_industry),
            company_info=company_info,
            company_culture=company_culture,
            hiring_trends=hiring_trends,
            connection_types=connection_types,
            potential_contacts=potential_contacts,
            alumni_connections=alumni_connections,
            industry_connections=industry_connections,
            recruiter_insights=recruiter_insights,
            outreach_templates=outreach_templates,
            conversation_starters=result.get("conversation_starters", []),
            follow_up_strategies=follow_up_strategies,
            talking_points=result.get("talking_points", []),
            networking_events=networking_events,
            online_communities=online_communities,
            content_strategy=content_strategy,
            warm_introduction_paths=warm_introduction_paths,
            action_plan=action_plan,
            mutual_interests=result.get("mutual_interests", []),
            networking_score=result.get("networking_score", 0.0)
        )

        # Update run status
        _network_intelligence_runs[run_id].status = AgentStatus.COMPLETED
        _network_intelligence_runs[run_id].completed_at = datetime.utcnow()
        _network_intelligence_runs[run_id].result = network_result
        _network_intelligence_runs[run_id].messages.extend(result.get("messages", []))
        _network_intelligence_runs[run_id].messages.append(
            f"Completed! Networking score: {network_result.networking_score:.0f}/100"
        )

        if result.get("errors"):
            _network_intelligence_runs[run_id].errors.extend(result["errors"])

    except Exception as e:
        logger.error(f"Network Intelligence agent error: {e}")
        _network_intelligence_runs[run_id].status = AgentStatus.FAILED
        _network_intelligence_runs[run_id].errors.append(str(e))
        _network_intelligence_runs[run_id].completed_at = datetime.utcnow()


@router.post("/network/analyze", response_model=NetworkIntelligenceResponse)
async def start_network_intelligence(
    request: NetworkIntelligenceRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a Network Intelligence agent run.

    Analyzes networking opportunities at a target company and provides:
    - Company culture and hiring insights
    - Connection type recommendations
    - Outreach templates and strategies
    - Networking event suggestions
    - Action plan with immediate steps
    """
    run_id = str(uuid4())

    # Create initial response
    response = NetworkIntelligenceResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=str(current_user.id),
        started_at=datetime.utcnow(),
        messages=[f"Network Intelligence analysis queued for {request.target_company}"]
    )

    # Store and start background task
    _network_intelligence_runs[run_id] = response
    background_tasks.add_task(
        run_network_intelligence_agent,
        run_id,
        str(current_user.id),
        request
    )

    return response


@router.get("/network/status/{run_id}", response_model=NetworkIntelligenceStatusResponse)
async def get_network_intelligence_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Network Intelligence run."""
    if run_id not in _network_intelligence_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _network_intelligence_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    # Calculate progress based on messages
    progress = 0.0
    current_step = "Queued"

    if run.status == AgentStatus.RUNNING:
        messages = run.messages
        if any("action plan" in m.lower() for m in messages):
            progress = 90.0
            current_step = "Creating action plan"
        elif any("outreach" in m.lower() for m in messages):
            progress = 75.0
            current_step = "Generating outreach strategies"
        elif any("opportunities" in m.lower() for m in messages):
            progress = 60.0
            current_step = "Finding networking opportunities"
        elif any("connection" in m.lower() for m in messages):
            progress = 40.0
            current_step = "Identifying connection types"
        elif any("research" in m.lower() for m in messages):
            progress = 25.0
            current_step = "Researching company"
        elif any("profile" in m.lower() for m in messages):
            progress = 15.0
            current_step = "Loading user profile"
        else:
            progress = 10.0
            current_step = "Initializing"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return NetworkIntelligenceStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/network/result/{run_id}", response_model=NetworkIntelligenceResponse)
async def get_network_intelligence_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Network Intelligence run."""
    if run_id not in _network_intelligence_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _network_intelligence_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run


# ============================================================================
# AUTO-APPLY AGENT ENDPOINTS
# ============================================================================

async def run_auto_apply_agent_task(
    run_id: str,
    user_id: str,
    request: AutoApplyRequest
):
    """Background task to run the Auto-Apply agent."""
    from backend.agents.auto_apply_agent import run_auto_apply_agent

    try:
        # Update status to running
        _auto_apply_runs[run_id].status = AgentStatus.RUNNING
        _auto_apply_runs[run_id].messages.append("Starting Auto-Apply agent...")
        _auto_apply_runs[run_id].messages.append(f"Analyzing job: {request.job_title} at {request.company_name}...")

        # Status callback for progress updates
        def status_callback(message: str):
            _auto_apply_runs[run_id].messages.append(message)

        # Run the agent with correct parameters
        result = await run_auto_apply_agent(
            user_id=user_id,
            job_title=request.job_title,
            company_name=request.company_name,
            job_description=request.job_description,
            job_url=request.job_url,
            application_type=request.application_type,
            status_callback=status_callback
        )

        # Build fit assessment from result
        fit_assessment_data = result.get("fit_assessment", {})
        fit_assessment = None
        if fit_assessment_data:
            skills_match_data = fit_assessment_data.get("skills_match", {})
            experience_match_data = fit_assessment_data.get("experience_match", {})
            fit_assessment = FitAssessment(
                overall_match_score=fit_assessment_data.get("overall_match_score", 0),
                recommendation=fit_assessment_data.get("recommendation", ""),
                strengths=fit_assessment_data.get("strengths", []),
                gaps=fit_assessment_data.get("gaps", []),
                positioning_strategy=fit_assessment_data.get("positioning_strategy", ""),
                red_flags=fit_assessment_data.get("red_flags", []),
                interview_likelihood=fit_assessment_data.get("interview_likelihood", ""),
                skills_match=SkillsMatch(
                    score=skills_match_data.get("score", 0),
                    matched_skills=skills_match_data.get("matched_skills", skills_match_data.get("matched", [])),
                    missing_skills=skills_match_data.get("missing_skills", skills_match_data.get("missing", [])),
                    transferable_skills=skills_match_data.get("transferable_skills", skills_match_data.get("transferable", []))
                ) if skills_match_data else None,
                experience_match=ExperienceMatchAssessment(
                    score=experience_match_data.get("score", 0),
                    assessment=experience_match_data.get("assessment", "")
                ) if experience_match_data else None
            )

        # Build follow-up plan from result
        follow_up_data = result.get("follow_up_plan", {})
        follow_up_plan = None
        if follow_up_data:
            follow_up_plan = FollowUpPlan(
                application_submitted=follow_up_data.get("application_submitted", ""),
                follow_up_timeline=[
                    FollowUpAction(**a) for a in follow_up_data.get("follow_up_timeline", [])
                ] if follow_up_data.get("follow_up_timeline") else [],
                recruiter_outreach=RecruiterOutreach(**follow_up_data.get("recruiter_outreach", {})) if follow_up_data.get("recruiter_outreach") else None,
                interview_prep_tasks=follow_up_data.get("interview_prep_tasks", []),
                backup_actions=follow_up_data.get("backup_actions", []),
                success_indicators=follow_up_data.get("success_indicators", [])
            )

        # Build form data from result
        form_data = None
        form_data_raw = result.get("form_data", {})
        if form_data_raw and isinstance(form_data_raw, dict):
            form_data = FormFieldData(**form_data_raw)

        # Store the result
        _auto_apply_runs[run_id].result = AutoApplyResult(
            job_title=request.job_title,
            company_name=request.company_name,
            application_score=result.get("application_score", 0),
            job_requirements=JobRequirements(**result.get("job_requirements", {})) if result.get("job_requirements") else None,
            fit_assessment=fit_assessment,
            cover_letter=result.get("cover_letter", ""),
            customized_resume_points=result.get("customized_resume_points", []),
            skills_to_highlight=result.get("skills_to_highlight", []),
            key_achievements=result.get("key_achievements", []),
            ats_optimization_tips=result.get("ats_optimization_tips", []),
            screening_questions=[
                ScreeningQuestion(**q) for q in result.get("screening_questions", [])
            ] if result.get("screening_questions") else [],
            form_data=form_data,
            follow_up_plan=follow_up_plan
        )

        _auto_apply_runs[run_id].status = AgentStatus.COMPLETED
        _auto_apply_runs[run_id].completed_at = datetime.utcnow()
        score = result.get("application_score", 0)
        _auto_apply_runs[run_id].messages.append(f"Completed! Application score: {score}/100")

    except Exception as e:
        logger.error(f"Auto-Apply agent error: {e}")
        _auto_apply_runs[run_id].status = AgentStatus.FAILED
        _auto_apply_runs[run_id].errors.append(str(e))
        _auto_apply_runs[run_id].completed_at = datetime.utcnow()


@router.post("/apply/prepare", response_model=AutoApplyResponse)
async def prepare_application(
    request: AutoApplyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Prepare a job application with AI assistance.

    This agent analyzes the job posting, assesses fit, generates a cover letter,
    prepares screening question answers, and creates a follow-up plan.

    Returns a run_id that can be used to check status and retrieve results.
    """
    run_id = str(uuid4())
    user_id = str(current_user.id)

    # Initialize the run
    run = AutoApplyResponse(
        run_id=run_id,
        status=AgentStatus.PENDING,
        user_id=user_id,
        started_at=datetime.utcnow(),
        messages=[f"Application preparation queued for {request.job_title} at {request.company_name}"]
    )
    _auto_apply_runs[run_id] = run

    # Start background task
    background_tasks.add_task(
        run_auto_apply_agent_task,
        run_id,
        user_id,
        request
    )

    return run


@router.get("/apply/status/{run_id}", response_model=AutoApplyStatusResponse)
async def get_auto_apply_status(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of an Auto-Apply agent run."""
    if run_id not in _auto_apply_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _auto_apply_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    # Calculate progress based on messages
    progress = 0.0
    current_step = "Queued"

    if run.status == AgentStatus.RUNNING:
        messages = run.messages
        if any("follow-up" in m.lower() or "follow up" in m.lower() for m in messages):
            progress = 90.0
            current_step = "Preparing follow-up plan"
        elif any("form" in m.lower() or "screening" in m.lower() for m in messages):
            progress = 75.0
            current_step = "Generating form data"
        elif any("cover letter" in m.lower() or "customiz" in m.lower() for m in messages):
            progress = 55.0
            current_step = "Customizing application materials"
        elif any("fit" in m.lower() or "assess" in m.lower() for m in messages):
            progress = 35.0
            current_step = "Assessing job fit"
        elif any("analyz" in m.lower() or "job" in m.lower() for m in messages):
            progress = 20.0
            current_step = "Analyzing job requirements"
        elif any("profile" in m.lower() or "resume" in m.lower() for m in messages):
            progress = 10.0
            current_step = "Loading user profile"
        else:
            progress = 5.0
            current_step = "Initializing"
    elif run.status == AgentStatus.COMPLETED:
        progress = 100.0
        current_step = "Complete"
    elif run.status == AgentStatus.FAILED:
        progress = 0.0
        current_step = "Failed"

    return AutoApplyStatusResponse(
        run_id=run_id,
        status=run.status,
        progress_percent=progress,
        current_step=current_step,
        messages=run.messages,
        errors=run.errors
    )


@router.get("/apply/result/{run_id}", response_model=AutoApplyResponse)
async def get_auto_apply_result(
    run_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full result of a completed Auto-Apply run."""
    if run_id not in _auto_apply_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _auto_apply_runs[run_id]

    # Verify ownership
    if run.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")

    return run
