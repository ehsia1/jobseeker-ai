"""Schemas for Agent API endpoints."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunRequest(BaseModel):
    """Request to start an agent run."""
    keywords: Optional[List[str]] = Field(
        default=None,
        description="Custom keywords to search for (overrides profile-based search)"
    )
    profession: Optional[str] = Field(
        default=None,
        description="Profession filter (e.g., 'software_engineer', 'data_scientist')"
    )
    remote_only: bool = Field(
        default=True,
        description="Only search for remote jobs"
    )
    min_score: float = Field(
        default=70.0,
        ge=0,
        le=100,
        description="Minimum match score threshold"
    )
    generate_proposals: bool = Field(
        default=True,
        description="Generate proposals for top matches"
    )
    max_proposals: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of proposals to generate"
    )


class JobMatchResult(BaseModel):
    """A single job match result."""
    job_id: str
    title: str
    company: str
    location: Optional[str] = None
    remote: bool = False
    score: float
    explanation: Optional[str] = None
    proposal: Optional[str] = None


class AgentRunResponse(BaseModel):
    """Response from an agent run."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    jobs_found: int = 0
    jobs_scored: int = 0
    matches_found: int = 0
    proposals_generated: int = 0

    # Top matches with details
    top_matches: List[JobMatchResult] = []

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class AgentRunStatusResponse(BaseModel):
    """Status of an agent run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


class AgentHealthResponse(BaseModel):
    """Agent service health check response."""
    status: str
    llm_provider: str
    llm_available: bool
    supported_features: List[str]


# Interview Prep Agent Schemas

class InterviewPrepRequest(BaseModel):
    """Request to start an interview prep session."""
    job_id: Optional[str] = Field(
        default=None,
        description="Job ID to tailor interview prep for (optional)"
    )
    interview_type: str = Field(
        default="auto",
        description="Interview type: behavioral, technical, system_design, case_study, auto"
    )
    difficulty: str = Field(
        default="mid",
        description="Difficulty level: entry, mid, senior, lead, executive"
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of practice questions to generate"
    )


class InterviewPlan(BaseModel):
    """Interview preparation plan details."""
    interview_type: str
    difficulty: str
    focus_areas: List[str] = []
    skill_gaps_to_address: List[str] = []
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    recommended_frameworks: List[str] = []
    question_types: List[str] = []


class InterviewPrepResponse(BaseModel):
    """Response from interview prep agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    session_id: Optional[str] = None
    interview_plan: Optional[InterviewPlan] = None
    prep_tips: List[str] = []
    focus_areas: List[str] = []
    skill_gaps: List[str] = []
    questions_generated: int = 0

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class InterviewPrepStatusResponse(BaseModel):
    """Status of an interview prep run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []
