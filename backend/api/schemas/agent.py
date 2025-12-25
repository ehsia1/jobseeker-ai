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
        default=40.0,
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


# Resume Optimization Agent Schemas

class ResumeOptimizationRequest(BaseModel):
    """Request to start a resume optimization run."""
    job_id: Optional[str] = Field(
        default=None,
        description="Target job ID to optimize resume for (optional)"
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Job description text to optimize for (alternative to job_id)"
    )
    optimization_focus: str = Field(
        default="balanced",
        description="Optimization focus: ats, impact, keywords, balanced"
    )
    include_cover_letter: bool = Field(
        default=False,
        description="Also generate a tailored cover letter"
    )
    preserve_formatting: bool = Field(
        default=True,
        description="Try to preserve original resume structure"
    )


class ResumeSection(BaseModel):
    """A section of the optimized resume."""
    section_name: str
    original_content: Optional[str] = None
    optimized_content: str
    improvement_notes: List[str] = []
    keywords_added: List[str] = []


class ATSScore(BaseModel):
    """ATS compatibility score breakdown."""
    overall_score: int = Field(ge=0, le=100)
    keyword_match: int = Field(ge=0, le=100)
    formatting_score: int = Field(ge=0, le=100)
    section_completeness: int = Field(ge=0, le=100)
    readability_score: int = Field(ge=0, le=100)
    issues: List[str] = []
    suggestions: List[str] = []


class ResumeOptimizationResult(BaseModel):
    """Result of resume optimization."""
    optimized_sections: List[ResumeSection] = []
    ats_score_before: Optional[ATSScore] = None
    ats_score_after: Optional[ATSScore] = None
    keywords_matched: List[str] = []
    keywords_missing: List[str] = []
    skills_highlighted: List[str] = []
    improvement_summary: str = ""
    cover_letter: Optional[str] = None


class ResumeOptimizationResponse(BaseModel):
    """Response from resume optimization agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[ResumeOptimizationResult] = None
    target_job_title: Optional[str] = None
    target_company: Optional[str] = None

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class ResumeOptimizationStatusResponse(BaseModel):
    """Status of a resume optimization run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


# Application Tracker Agent Schemas

class ApplicationTrackerRequest(BaseModel):
    """Request to get application portfolio briefing."""
    briefing_type: str = Field(
        default="daily",
        description="Briefing type: daily, weekly, full"
    )


class PortfolioAnalysis(BaseModel):
    """Analysis of the application portfolio."""
    health_score: int = Field(ge=0, le=100, description="Overall portfolio health score")
    total_count: int = 0
    active_count: int = 0
    interview_count: int = 0
    offer_count: int = 0
    response_rate: float = 0.0
    activity_trend: str = "moderate"
    insights: List[str] = []
    status_distribution: Dict[str, int] = {}


class StaleApplication(BaseModel):
    """An application that needs attention."""
    application_id: str
    job_title: str
    company: str
    status: str
    days_stale: int
    threshold: int
    urgency: str  # high, medium
    reason: str


class Recommendation(BaseModel):
    """Strategic recommendation for job search."""
    type: str  # strategy, preparation
    title: str
    description: str
    priority: str  # high, medium, low


class ActionItem(BaseModel):
    """Action item requiring user attention."""
    type: str  # follow_up, reminder, upcoming
    priority: str  # high, medium, low
    title: str
    description: str
    application_id: Optional[str] = None
    reminder_id: Optional[str] = None


class ApplicationStats(BaseModel):
    """Quick application statistics."""
    total_applications: int = 0
    active_applications: int = 0
    response_rate: float = 0.0
    upcoming_reminders: int = 0
    overdue_reminders: int = 0
    by_status: Dict[str, int] = {}


class ApplicationTrackerResponse(BaseModel):
    """Response from application tracker agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    briefing: str = ""
    portfolio_analysis: Optional[PortfolioAnalysis] = None
    stale_applications: List[StaleApplication] = []
    recommendations: List[Recommendation] = []
    action_items: List[ActionItem] = []
    stats: Optional[ApplicationStats] = None

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class ApplicationTrackerStatusResponse(BaseModel):
    """Status of an application tracker run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


class QuickStatsResponse(BaseModel):
    """Quick application stats for dashboard."""
    success: bool
    total_applications: int = 0
    active_applications: int = 0
    response_rate: float = 0.0
    upcoming_reminders: int = 0
    overdue_reminders: int = 0
    by_status: Dict[str, int] = {}
    error: Optional[str] = None


# Cover Letter Agent Schemas

class CoverLetterStyle(str, Enum):
    """Cover letter writing styles."""
    TRADITIONAL = "traditional"  # Formal, conservative industries
    MODERN = "modern"  # Contemporary, tech-friendly
    CREATIVE = "creative"  # Startups, creative industries
    EXECUTIVE = "executive"  # Senior/leadership roles


class CoverLetterLength(str, Enum):
    """Cover letter length options."""
    CONCISE = "concise"  # 200-250 words
    STANDARD = "standard"  # 300-400 words
    DETAILED = "detailed"  # 450-550 words


class CoverLetterRequest(BaseModel):
    """Request to generate a cover letter."""
    job_id: Optional[str] = Field(
        default=None,
        description="Job ID to tailor cover letter for (optional)"
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Job description text (alternative to job_id)"
    )
    style: str = Field(
        default="modern",
        description="Writing style: traditional, modern, creative, executive"
    )
    length: str = Field(
        default="standard",
        description="Letter length: concise, standard, detailed"
    )
    include_salary_expectations: bool = Field(
        default=False,
        description="Include salary expectations if known"
    )
    emphasize_remote: bool = Field(
        default=False,
        description="Emphasize remote work experience and preferences"
    )


class CoverLetterRegenerateRequest(BaseModel):
    """Request to regenerate a cover letter with feedback."""
    original_letter: str = Field(
        description="The original cover letter to improve"
    )
    feedback: str = Field(
        description="Feedback or instructions for regeneration"
    )
    job_id: Optional[str] = Field(
        default=None,
        description="Job ID for context"
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Job description text for context"
    )


class SkillAlignment(BaseModel):
    """Skill alignment analysis between resume and job."""
    matched_skills: List[str] = []
    partial_matches: List[str] = []
    missing_skills: List[str] = []
    alignment_score: float = 0.0
    summary: str = ""


class ExperienceMatch(BaseModel):
    """A matched experience from the resume."""
    experience_title: str
    relevance_score: float
    matched_keywords: List[str] = []
    highlight_points: List[str] = []


class CoverLetterResult(BaseModel):
    """Result of cover letter generation."""
    cover_letter: str
    ats_score: int = Field(ge=0, le=100)
    keywords_used: List[str] = []
    keywords_missing: List[str] = []
    skill_alignment: Optional[SkillAlignment] = None
    experience_matches: List[ExperienceMatch] = []
    suggestions: List[str] = []


class CoverLetterResponse(BaseModel):
    """Response from cover letter agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[CoverLetterResult] = None
    target_job_title: Optional[str] = None
    target_company: Optional[str] = None
    style_used: Optional[str] = None
    length_used: Optional[str] = None

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class CoverLetterStatusResponse(BaseModel):
    """Status of a cover letter generation run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


# Salary Research & Negotiation Agent Schemas

class JobLevel(str, Enum):
    """Job level options for salary research."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    LEAD = "lead"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"


class SalaryResearchRequest(BaseModel):
    """Request to research salary data and negotiation strategies."""
    job_title: str = Field(
        description="Job title to research salary for"
    )
    location: str = Field(
        default="Remote",
        description="Location for cost of living adjustment"
    )
    years_experience: int = Field(
        default=5,
        ge=0,
        le=50,
        description="Years of relevant experience"
    )
    current_salary: Optional[float] = Field(
        default=None,
        description="Current salary for comparison (optional)"
    )
    target_salary: Optional[float] = Field(
        default=None,
        description="Target salary to negotiate for (optional)"
    )
    company_name: Optional[str] = Field(
        default=None,
        description="Target company name for company-specific research"
    )
    job_level: str = Field(
        default="mid",
        description="Job level: entry, mid, senior, staff, lead, principal, executive"
    )
    include_negotiation_scripts: bool = Field(
        default=True,
        description="Generate negotiation scripts and email templates"
    )


class SalaryRange(BaseModel):
    """Salary range data."""
    min: float = 0
    p25: float = 0
    median: float = 0
    p75: float = 0
    max: float = 0


class EquityComponent(BaseModel):
    """Equity compensation details."""
    typical_grant_value: float = 0
    annual_value: float = 0
    vesting_schedule: str = "4-year with 1-year cliff"
    type: str = "RSU"


class BonusComponent(BaseModel):
    """Bonus compensation details."""
    target_percent: float = 0
    typical_range: str = ""
    timing: str = "Annual"


class BenefitsValue(BaseModel):
    """Benefits valuation."""
    health_insurance: float = 0
    retirement_match: float = 0
    other_benefits: float = 0
    total_annual: float = 0


class CompensationAnalysis(BaseModel):
    """Full compensation breakdown."""
    base_salary_weight: float = 70
    equity_component: Optional[EquityComponent] = None
    bonus_component: Optional[BonusComponent] = None
    benefits_value: Optional[BenefitsValue] = None
    additional_perks: List[str] = []
    remote_premium_or_discount: float = 0
    negotiable_components: List[str] = []


class CommonObjection(BaseModel):
    """Common negotiation objection and response."""
    objection: str
    response: str


class NegotiationStrategy(BaseModel):
    """Negotiation strategy details."""
    recommended_ask: float = 0
    walk_away_point: float = 0
    anchor_high_rationale: str = ""
    timing_advice: str = ""
    opening_approach: str = ""
    key_talking_points: List[str] = []
    common_objections: List[CommonObjection] = []
    alternatives_to_negotiate: List[str] = []
    risk_level: str = "medium"
    confidence_score: int = 50


class NegotiationScript(BaseModel):
    """A negotiation script for a specific scenario."""
    scenario: str
    script: str
    tone: str


class MarketData(BaseModel):
    """Market salary data."""
    base_salary: Optional[SalaryRange] = None
    total_compensation: Optional[Dict[str, float]] = None
    typical_bonus_percent: float = 0
    typical_equity_value: float = 0
    market_demand: str = "medium"
    salary_trend: str = "stable"
    key_factors: List[str] = []
    data_sources: List[str] = []


class SalaryResearchResult(BaseModel):
    """Result of salary research."""
    job_title: str
    location: str
    salary_range: SalaryRange
    market_data: Optional[MarketData] = None
    compensation_analysis: Optional[CompensationAnalysis] = None
    total_comp_estimate: float = 0
    location_adjustment: float = 1.0
    experience_adjustment: float = 1.0
    negotiation_leverage: List[str] = []
    negotiation_strategy: Optional[NegotiationStrategy] = None
    negotiation_scripts: List[NegotiationScript] = []
    counter_offer_template: str = ""


class SalaryResearchResponse(BaseModel):
    """Response from salary research agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[SalaryResearchResult] = None

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class SalaryResearchStatusResponse(BaseModel):
    """Status of a salary research run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


# Skill Gap & Career Development Agent Schemas

class SkillGapRequest(BaseModel):
    """Request to analyze skill gaps and get learning recommendations."""
    target_job_title: str = Field(
        description="Target job title to analyze skills for"
    )
    target_job_description: Optional[str] = Field(
        default=None,
        description="Optional job description text for more specific analysis"
    )
    target_industry: str = Field(
        default="technology",
        description="Target industry (e.g., technology, finance, healthcare)"
    )
    target_company: Optional[str] = Field(
        default=None,
        description="Target company name for company-specific insights"
    )
    timeframe_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="How many months you have to acquire new skills"
    )
    learning_hours_per_week: int = Field(
        default=10,
        ge=1,
        le=40,
        description="Hours per week available for learning"
    )
    include_certifications: bool = Field(
        default=True,
        description="Include certification recommendations"
    )
    include_projects: bool = Field(
        default=True,
        description="Include project recommendations for portfolio"
    )
    focus_area: str = Field(
        default="both",
        description="Focus area: technical, soft_skills, both"
    )


class SkillGap(BaseModel):
    """A single skill gap identified."""
    skill: str
    gap_level: str = "not_present"  # not_present, needs_improvement, minor_gap
    priority: str = "medium"  # high, medium, low
    category: str = "technical"  # technical, soft_skill, domain_knowledge, tool
    learning_effort: str = "weeks"  # weeks, months, long_term
    prerequisite_skills: List[str] = []


class LearningResource(BaseModel):
    """A recommended learning resource."""
    skill: str
    name: str
    type: str = "online_course"  # online_course, book, tutorial, bootcamp, video_series, documentation
    provider: str = ""
    url: Optional[str] = None
    duration_hours: int = 0
    cost: str = "free"  # free, $, $$, $$$
    difficulty: str = "intermediate"  # beginner, intermediate, advanced
    rating: float = 0.0
    key_topics: List[str] = []


class RecommendedCertification(BaseModel):
    """A recommended certification."""
    name: str
    provider: str
    skill: str
    cost_range: str = ""
    prep_time_months: int = 1
    career_value: str = "medium"  # high, medium, low
    prerequisites: List[str] = []


class RecommendedProject(BaseModel):
    """A recommended portfolio project."""
    title: str
    description: str
    skills_practiced: List[str] = []
    difficulty: str = "intermediate"  # beginner, intermediate, advanced
    estimated_hours: int = 0
    portfolio_value: str = "medium"  # high, medium, low


class RoadmapActivity(BaseModel):
    """An activity in the learning roadmap."""
    type: str  # course, project, certification_prep, practice
    name: str
    hours_per_week: int = 0
    description: str = ""


class RoadmapPhase(BaseModel):
    """A phase in the learning roadmap."""
    phase_number: int
    name: str
    duration_weeks: int = 4
    focus_skills: List[str] = []
    activities: List[RoadmapActivity] = []
    milestones: List[str] = []
    success_metrics: List[str] = []


class RoadmapMilestone(BaseModel):
    """A key milestone in the learning journey."""
    month: int
    milestone: str
    skills_acquired: List[str] = []


class LearningRoadmap(BaseModel):
    """Complete learning roadmap."""
    total_duration_months: int = 6
    phases: List[RoadmapPhase] = []
    weekly_schedule_template: Dict[str, str] = {}
    key_milestones: List[RoadmapMilestone] = []
    job_ready_indicators: List[str] = []


class SkillGapResult(BaseModel):
    """Result of skill gap analysis."""
    target_job_title: str
    target_industry: str = ""
    current_skills: List[str] = []
    skill_gaps: List[SkillGap] = []
    transferable_skills: List[str] = []
    skill_overlap_percent: float = 0.0
    market_demand: Dict[str, str] = {}
    salary_impact: Dict[str, float] = {}
    learning_resources: List[LearningResource] = []
    recommended_certifications: List[RecommendedCertification] = []
    recommended_projects: List[RecommendedProject] = []
    learning_roadmap: Optional[LearningRoadmap] = None
    quick_wins: List[str] = []
    long_term_investments: List[str] = []


class SkillGapResponse(BaseModel):
    """Response from skill gap agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[SkillGapResult] = None

    # Progress messages
    messages: List[str] = []
    errors: List[str] = []


class SkillGapStatusResponse(BaseModel):
    """Status of a skill gap analysis run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


# =============================================================================
# Network Intelligence Agent Schemas
# =============================================================================


class NetworkIntelligenceRequest(BaseModel):
    """Request to analyze networking opportunities at a target company."""
    target_company: str = Field(description="Name of the target company")
    target_role: Optional[str] = Field(default=None, description="Specific role being targeted")
    target_industry: str = Field(default="technology", description="Industry of the target company")
    networking_goals: List[str] = Field(
        default=["Build connections", "Learn about opportunities"],
        description="Goals for networking"
    )


class CompanyInfo(BaseModel):
    """Information about the target company."""
    size: str = ""
    industry_focus: str = ""
    key_departments: List[str] = []
    headquarters: str = ""
    remote_culture: str = ""
    growth_stage: str = ""
    recent_news: List[str] = []


class CompanyCulture(BaseModel):
    """Company culture information."""
    values: List[str] = []
    work_style: str = ""
    employee_reviews_themes: List[str] = []
    innovation_focus: str = ""
    diversity_initiatives: List[str] = []


class HiringTrends(BaseModel):
    """Hiring trends at the company."""
    current_openings_estimate: str = ""
    hot_skills: List[str] = []
    typical_hiring_process: str = ""
    interview_style: str = ""
    growth_areas: List[str] = []


class ConnectionType(BaseModel):
    """A type of connection to pursue."""
    type: str = ""
    priority: str = "medium"
    rationale: str = ""
    where_to_find: List[str] = []
    approach_style: str = ""
    expected_value: str = ""


class AlumniConnection(BaseModel):
    """Alumni-based connection opportunity."""
    school_or_company: str = ""
    connection_strength: str = "medium"
    outreach_angle: str = ""
    suggested_platforms: List[str] = []


class IndustryConnection(BaseModel):
    """Industry-based connection opportunity."""
    connection_type: str = ""
    relevance: str = ""
    how_to_connect: str = ""
    common_ground: List[str] = []


class RecruiterInsight(BaseModel):
    """Insight about recruiters."""
    recruiter_type: str = ""
    how_to_find: str = ""
    approach_timing: str = ""
    what_they_value: str = ""


class PotentialContact(BaseModel):
    """A potential contact to reach out to."""
    role_type: str = ""
    department: str = ""
    seniority: str = ""
    value_proposition: str = ""
    ask: str = ""
    approach_platform: str = ""


class OutreachTemplate(BaseModel):
    """Template for outreach messages."""
    scenario: str = ""
    target_role: str = ""
    platform: str = ""
    subject_line: str = ""
    message: str = ""
    call_to_action: str = ""
    tone: str = ""
    length: str = ""
    personalization_tips: List[str] = []


class FollowUpStrategy(BaseModel):
    """Strategy for following up."""
    scenario: str = ""
    timing: str = ""
    approach: str = ""
    message_template: str = ""
    persistence_limit: str = ""


class NetworkingEvent(BaseModel):
    """A networking event opportunity."""
    event_type: str = ""
    name: str = ""
    frequency: str = ""
    relevance: str = ""
    how_to_maximize: str = ""
    likely_attendees: List[str] = []
    cost: str = ""
    location_type: str = ""


class OnlineCommunity(BaseModel):
    """An online community for networking."""
    platform: str = ""
    community_name: str = ""
    activity_level: str = ""
    member_profile: str = ""
    engagement_strategy: str = ""
    connection_potential: str = ""


class ContentStrategy(BaseModel):
    """Content strategy for visibility."""
    platforms: List[str] = []
    content_types: List[str] = []
    topics: List[str] = []
    posting_frequency: str = ""
    engagement_tactics: List[str] = []
    hashtags_or_keywords: List[str] = []


class WarmIntroductionPath(BaseModel):
    """A path to get a warm introduction."""
    path: str = ""
    starting_point: str = ""
    intermediate_steps: List[str] = []
    success_likelihood: str = ""
    time_estimate: str = ""


class ImmediateAction(BaseModel):
    """An immediate action to take."""
    action: str = ""
    priority: str = ""
    time_required: str = ""
    expected_outcome: str = ""
    resources_needed: List[str] = []


class WeeklyTask(BaseModel):
    """A weekly recurring task."""
    task: str = ""
    frequency: str = ""
    platform: str = ""
    goal: str = ""


class MilestoneTarget(BaseModel):
    """A milestone to achieve."""
    milestone: str = ""
    timeframe: str = ""
    success_criteria: str = ""
    dependencies: List[str] = []


class NetworkingMetric(BaseModel):
    """A metric to track."""
    metric: str = ""
    target: str = ""
    tracking_method: str = ""


class RiskMitigation(BaseModel):
    """Risk mitigation strategy."""
    risk: str = ""
    mitigation: str = ""


class NetworkingActionPlan(BaseModel):
    """Complete networking action plan."""
    immediate_actions: List[ImmediateAction] = []
    weekly_tasks: List[WeeklyTask] = []
    milestone_targets: List[MilestoneTarget] = []
    metrics_to_track: List[NetworkingMetric] = []
    risk_mitigation: List[RiskMitigation] = []


class NetworkIntelligenceResult(BaseModel):
    """Full result from Network Intelligence Agent."""
    target_company: str = ""
    target_role: Optional[str] = None
    target_industry: str = ""

    # Company intelligence
    company_info: CompanyInfo = Field(default_factory=CompanyInfo)
    company_culture: CompanyCulture = Field(default_factory=CompanyCulture)
    hiring_trends: HiringTrends = Field(default_factory=HiringTrends)

    # Connections
    connection_types: List[ConnectionType] = []
    potential_contacts: List[PotentialContact] = []
    alumni_connections: List[AlumniConnection] = []
    industry_connections: List[IndustryConnection] = []
    recruiter_insights: List[RecruiterInsight] = []

    # Outreach
    outreach_templates: List[OutreachTemplate] = []
    conversation_starters: List[str] = []
    follow_up_strategies: List[FollowUpStrategy] = []
    talking_points: List[str] = []

    # Opportunities
    networking_events: List[NetworkingEvent] = []
    online_communities: List[OnlineCommunity] = []
    content_strategy: ContentStrategy = Field(default_factory=ContentStrategy)
    warm_introduction_paths: List[WarmIntroductionPath] = []

    # Plan
    action_plan: NetworkingActionPlan = Field(default_factory=NetworkingActionPlan)
    mutual_interests: List[str] = []
    networking_score: float = 0.0


class NetworkIntelligenceResponse(BaseModel):
    """Response from Network Intelligence Agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[NetworkIntelligenceResult] = None
    messages: List[str] = []
    errors: List[str] = []


class NetworkIntelligenceStatusResponse(BaseModel):
    """Status of a network intelligence run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []


# =============================================================================
# Auto-Apply Agent Schemas
# =============================================================================


class ApplicationType(str, Enum):
    """Types of job applications."""
    QUICK_APPLY = "quick_apply"
    CUSTOM = "custom"
    FULL_FORM = "full_form"


class AutoApplyRequest(BaseModel):
    """Request to prepare a job application."""
    job_title: str = Field(description="Title of the job position")
    company_name: str = Field(description="Name of the company")
    job_description: str = Field(description="Full job description text")
    job_url: Optional[str] = Field(
        default=None,
        description="URL to the job posting (optional)"
    )
    application_type: str = Field(
        default="custom",
        description="Application type: quick_apply, custom, or full_form"
    )


class JobRequirements(BaseModel):
    """Extracted job requirements."""
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    experience_years: str = ""
    education_requirements: str = ""
    key_responsibilities: List[str] = []
    must_have_qualifications: List[str] = []
    keywords: List[str] = []
    company_values: List[str] = []
    role_level: str = ""
    remote_policy: str = ""
    salary_range: str = ""
    application_deadline: str = ""


class SkillsMatch(BaseModel):
    """Skills matching analysis."""
    score: int = 0
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    transferable_skills: List[str] = []


class ExperienceMatchAssessment(BaseModel):
    """Experience matching assessment."""
    score: int = 0
    assessment: str = ""


class FitAssessment(BaseModel):
    """Assessment of candidate fit for the role."""
    overall_match_score: int = 0
    skills_match: Optional[SkillsMatch] = None
    experience_match: Optional[ExperienceMatchAssessment] = None
    strengths: List[str] = []
    gaps: List[str] = []
    positioning_strategy: str = ""
    red_flags: List[str] = []
    interview_likelihood: str = ""
    recommendation: str = ""


class ScreeningQuestion(BaseModel):
    """A screening question and prepared answer."""
    question: str
    answer: str


class FormFieldData(BaseModel):
    """Common form field data."""
    desired_salary: str = ""
    start_date: str = ""
    work_authorization: str = ""
    willing_to_relocate: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    years_of_experience: str = ""
    highest_education: str = ""


class FollowUpAction(BaseModel):
    """A follow-up action in the timeline."""
    day: int
    action: str
    template: str = ""


class RecruiterOutreach(BaseModel):
    """Recruiter outreach strategy."""
    suggested_message: str = ""
    best_platforms: List[str] = []


class FollowUpPlan(BaseModel):
    """Complete follow-up strategy."""
    application_submitted: str = ""
    follow_up_timeline: List[FollowUpAction] = []
    recruiter_outreach: Optional[RecruiterOutreach] = None
    interview_prep_tasks: List[str] = []
    backup_actions: List[str] = []
    success_indicators: List[str] = []


class AutoApplyResult(BaseModel):
    """Full result from Auto-Apply Agent."""
    # Job analysis
    job_title: str = ""
    company_name: str = ""
    job_requirements: Optional[JobRequirements] = None

    # Fit assessment
    fit_assessment: Optional[FitAssessment] = None
    application_score: float = 0.0

    # Customized materials
    customized_resume_points: List[str] = []
    cover_letter: str = ""
    skills_to_highlight: List[str] = []
    key_achievements: List[str] = []
    ats_optimization_tips: List[str] = []

    # Form data
    form_data: Optional[FormFieldData] = None
    screening_questions: List[ScreeningQuestion] = []

    # Follow-up
    follow_up_plan: Optional[FollowUpPlan] = None


class AutoApplyResponse(BaseModel):
    """Response from Auto-Apply Agent."""
    run_id: str
    status: AgentStatus
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[AutoApplyResult] = None
    messages: List[str] = []
    errors: List[str] = []


class AutoApplyStatusResponse(BaseModel):
    """Status of an auto-apply run."""
    run_id: str
    status: AgentStatus
    progress_percent: float = 0.0
    current_step: str = ""
    messages: List[str] = []
    errors: List[str] = []
