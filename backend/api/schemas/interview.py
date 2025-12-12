"""Interview coaching Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class InterviewTypeEnum(str, Enum):
    """Types of interview practice sessions."""

    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    CASE_STUDY = "case_study"
    SITUATIONAL = "situational"
    COMPETENCY = "competency"


class DifficultyLevelEnum(str, Enum):
    """Difficulty levels for interview questions."""

    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


# Request schemas
class CreateSessionRequest(BaseModel):
    """Request to create a new interview session."""

    interview_type: InterviewTypeEnum = Field(
        default=InterviewTypeEnum.BEHAVIORAL,
        description="Type of interview practice",
    )
    difficulty: DifficultyLevelEnum = Field(
        default=DifficultyLevelEnum.MID,
        description="Difficulty level",
    )
    job_id: Optional[UUID] = Field(
        None,
        description="Optional job ID to tailor questions",
    )
    target_role: Optional[str] = Field(
        None,
        max_length=255,
        description="Target job role",
    )
    target_company: Optional[str] = Field(
        None,
        max_length=255,
        description="Target company name",
    )
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Specific areas to focus on",
    )
    total_questions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of questions in session",
    )


class SubmitResponseRequest(BaseModel):
    """Request to submit a response to a question."""

    response: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="User's response to the question",
    )
    response_duration_seconds: Optional[int] = Field(
        None,
        ge=0,
        description="Time taken to respond in seconds",
    )


# Response schemas
class QuestionFeedbackResponse(BaseModel):
    """Feedback for a single interview question response."""

    score: int = Field(..., ge=0, le=100)
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    sample_answer: Optional[str] = None


class InterviewQuestionResponse(BaseModel):
    """Response schema for an interview question."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    question_order: int
    question_text: str
    question_category: Optional[str] = None
    expected_framework: Optional[str] = None

    # Response data (if answered)
    user_response: Optional[str] = None
    response_duration_seconds: Optional[int] = None
    answered_at: Optional[datetime] = None

    # Feedback data (if evaluated)
    feedback: Optional[str] = None
    score: Optional[int] = None
    strengths: Optional[List[str]] = None
    improvements: Optional[List[str]] = None
    sample_answer: Optional[str] = None

    asked_at: datetime

    @property
    def is_answered(self) -> bool:
        """Check if question has been answered."""
        return self.user_response is not None


class InterviewSessionResponse(BaseModel):
    """Response schema for an interview session."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: Optional[UUID] = None

    # Configuration
    interview_type: InterviewTypeEnum
    difficulty: DifficultyLevelEnum
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    focus_areas: Optional[List[str]] = None

    # Progress
    total_questions: int
    completed_questions: int
    overall_score: Optional[int] = None
    feedback_summary: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    # Related questions
    questions: List[InterviewQuestionResponse] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.completed_at is not None

    @property
    def progress_percentage(self) -> int:
        """Calculate progress percentage."""
        if self.total_questions == 0:
            return 0
        return int((self.completed_questions / self.total_questions) * 100)


class SessionSummaryResponse(BaseModel):
    """Summary of a completed interview session."""

    overall_score: int = Field(..., ge=0, le=100)
    total_questions: int
    completed_questions: int
    feedback_summary: str
    strengths: List[str] = Field(default_factory=list)
    areas_to_improve: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class SessionListItem(BaseModel):
    """List item for interview sessions."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    interview_type: InterviewTypeEnum
    difficulty: DifficultyLevelEnum
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    total_questions: int
    completed_questions: int
    overall_score: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.completed_at is not None


class SessionListResponse(BaseModel):
    """Response for listing interview sessions."""

    sessions: List[SessionListItem]
    total: int


class CurrentQuestionResponse(BaseModel):
    """Response for getting current question in a session."""

    session_id: UUID
    session_progress: int  # percentage
    question: Optional[InterviewQuestionResponse] = None
    is_session_complete: bool = False


class CreateSessionResponse(BaseModel):
    """Response after creating a new session."""

    session: InterviewSessionResponse
    current_question: InterviewQuestionResponse


class SubmitResponseResponse(BaseModel):
    """Response after submitting an answer."""

    feedback: QuestionFeedbackResponse
    session_progress: int  # percentage
    next_question: Optional[InterviewQuestionResponse] = None
    is_session_complete: bool = False


class InterviewHealthResponse(BaseModel):
    """Health check response for interview service."""

    status: str
    llm_available: bool
    supported_types: List[str]
    supported_difficulties: List[str]
