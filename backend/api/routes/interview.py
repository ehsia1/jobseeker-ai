"""Interview coaching routes for AI-powered interview practice."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.models.interview import InterviewType, DifficultyLevel
from backend.services.interview_service import InterviewCoachingService
from backend.api.schemas.interview import (
    CreateSessionRequest,
    CreateSessionResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
    InterviewSessionResponse,
    InterviewQuestionResponse,
    SessionListResponse,
    SessionListItem,
    SessionSummaryResponse,
    CurrentQuestionResponse,
    InterviewHealthResponse,
    InterviewTypeEnum,
    DifficultyLevelEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Optional OAuth2 scheme for demo mode compatibility
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user_or_demo(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user, or create/get demo user in demo mode."""
    # Demo mode: use demo user
    if settings.demo_mode and token is None:
        from uuid import uuid4

        # Get or create demo user
        result = await db.execute(
            select(User).where(User.email == "demo@localhost")
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid4(),
                email="demo@localhost",
                username="demo",
                password_hash="demo_not_used",
                is_active=True,
                is_premium=True,
            )
            db.add(user)
            await db.flush()

        return user

    # No token provided in non-demo mode
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    try:
        from jose import JWTError, jwt

        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Get user from database
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def _session_to_response(session) -> InterviewSessionResponse:
    """Convert InterviewSession model to response schema."""
    return InterviewSessionResponse(
        id=session.id,
        user_id=session.user_id,
        job_id=session.job_id,
        interview_type=InterviewTypeEnum(session.interview_type.value),
        difficulty=DifficultyLevelEnum(session.difficulty.value),
        target_role=session.target_role,
        target_company=session.target_company,
        focus_areas=session.focus_areas,
        total_questions=session.total_questions,
        completed_questions=session.completed_questions,
        overall_score=session.overall_score,
        feedback_summary=session.feedback_summary,
        created_at=session.created_at,
        updated_at=session.updated_at,
        completed_at=session.completed_at,
        questions=[_question_to_response(q) for q in (session.questions or [])],
    )


def _question_to_response(question) -> InterviewQuestionResponse:
    """Convert InterviewQuestion model to response schema."""
    return InterviewQuestionResponse(
        id=question.id,
        session_id=question.session_id,
        question_order=question.question_order,
        question_text=question.question_text,
        question_category=question.question_category,
        expected_framework=question.expected_framework,
        user_response=question.user_response,
        response_duration_seconds=question.response_duration_seconds,
        answered_at=question.answered_at,
        feedback=question.feedback,
        score=question.score,
        strengths=question.strengths,
        improvements=question.improvements,
        sample_answer=question.sample_answer,
        asked_at=question.asked_at,
    )


@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Create a new interview practice session.

    Start a new AI-powered interview practice session tailored to:
    - Interview type (behavioral, technical, system design, etc.)
    - Difficulty level (entry, mid, senior, lead, executive)
    - Target role and company (optional)
    - Specific focus areas (optional)

    The first question will be generated and included in the response.
    """
    try:
        service = InterviewCoachingService(db)

        # Convert enum types
        interview_type = InterviewType(request.interview_type.value)
        difficulty = DifficultyLevel(request.difficulty.value)

        session = await service.create_session(
            user_id=current_user.id,
            interview_type=interview_type,
            difficulty=difficulty,
            job_id=request.job_id,
            target_role=request.target_role,
            target_company=request.target_company,
            focus_areas=request.focus_areas,
            total_questions=request.total_questions,
        )

        await db.commit()

        # Re-fetch with relationships loaded
        session = await service.get_session(session.id)

        # Get the first question
        first_question = session.questions[0] if session.questions else None

        return CreateSessionResponse(
            session=_session_to_response(session),
            current_question=_question_to_response(first_question) if first_question else None,
        )

    except Exception as e:
        logger.error(f"Failed to create interview session: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interview session. Please try again.",
        )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 10,
    include_completed: bool = True,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """List user's interview practice sessions.

    Returns a list of interview sessions ordered by creation date (newest first).
    """
    service = InterviewCoachingService(db)
    sessions = await service.get_user_sessions(
        user_id=current_user.id,
        limit=limit,
        include_completed=include_completed,
    )

    items = [
        SessionListItem(
            id=s.id,
            interview_type=InterviewTypeEnum(s.interview_type.value),
            difficulty=DifficultyLevelEnum(s.difficulty.value),
            target_role=s.target_role,
            target_company=s.target_company,
            total_questions=s.total_questions,
            completed_questions=s.completed_questions,
            overall_score=s.overall_score,
            created_at=s.created_at,
            completed_at=s.completed_at,
        )
        for s in sessions
    ]

    return SessionListResponse(sessions=items, total=len(items))


@router.get("/sessions/{session_id}", response_model=InterviewSessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get an interview session by ID.

    Returns full session details including all questions and responses.
    """
    service = InterviewCoachingService(db)
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return _session_to_response(session)


@router.get("/sessions/{session_id}/current-question", response_model=CurrentQuestionResponse)
async def get_current_question(
    session_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get the current unanswered question in a session.

    Returns the next question to answer, or indicates if the session is complete.
    """
    service = InterviewCoachingService(db)

    # Get session to verify ownership
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Get current question
    question = await service.get_current_question(session_id)

    progress = int((session.completed_questions / session.total_questions) * 100) if session.total_questions > 0 else 0

    return CurrentQuestionResponse(
        session_id=session_id,
        session_progress=progress,
        question=_question_to_response(question) if question else None,
        is_session_complete=session.completed_at is not None or question is None,
    )


@router.post("/sessions/{session_id}/questions/{question_id}/respond", response_model=SubmitResponseResponse)
async def submit_response(
    session_id: UUID,
    question_id: UUID,
    request: SubmitResponseRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Submit a response to an interview question.

    After submitting your response, you'll receive:
    - A score (0-100)
    - Detailed feedback on your answer
    - Strengths identified in your response
    - Areas for improvement
    - A sample ideal answer for comparison

    The next question (if any) will also be included in the response.
    """
    service = InterviewCoachingService(db)

    # Verify session ownership
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    try:
        feedback = await service.submit_response(
            question_id=question_id,
            response=request.response,
            response_duration_seconds=request.response_duration_seconds,
        )

        await db.commit()

        # Get updated session
        session = await service.get_session(session_id)
        progress = int((session.completed_questions / session.total_questions) * 100) if session.total_questions > 0 else 0

        # Get next question if session not complete
        next_question = None
        is_complete = session.completed_questions >= session.total_questions
        if not is_complete:
            next_question = await service.get_current_question(session_id)

        return SubmitResponseResponse(
            feedback={
                "score": feedback.score,
                "feedback": feedback.feedback,
                "strengths": feedback.strengths,
                "improvements": feedback.improvements,
                "sample_answer": feedback.sample_answer,
            },
            session_progress=progress,
            next_question=_question_to_response(next_question) if next_question else None,
            is_session_complete=is_complete,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit response: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process response. Please try again.",
        )


@router.post("/sessions/{session_id}/complete", response_model=SessionSummaryResponse)
async def complete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Complete an interview session and get a summary.

    Marks the session as complete and generates a comprehensive summary including:
    - Overall score
    - Feedback summary
    - Top strengths demonstrated
    - Areas for improvement
    - Actionable recommendations
    """
    service = InterviewCoachingService(db)

    # Verify session ownership
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    try:
        summary = await service.complete_session(session_id)
        await db.commit()

        return SessionSummaryResponse(
            overall_score=summary.overall_score,
            total_questions=summary.total_questions,
            completed_questions=summary.completed_questions,
            feedback_summary=summary.feedback_summary,
            strengths=summary.strengths,
            areas_to_improve=summary.areas_to_improve,
            recommendations=summary.recommendations,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to complete session: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete session. Please try again.",
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Delete an interview session.

    Permanently removes the session and all associated questions/responses.
    """
    service = InterviewCoachingService(db)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this session",
        )

    await db.delete(session)
    await db.commit()
    return None


@router.get("/health", response_model=InterviewHealthResponse)
async def interview_health():
    """Check if the interview coaching service is operational."""
    from backend.services.llm_service import get_llm_service

    llm = get_llm_service()
    is_available = llm.is_available()

    return InterviewHealthResponse(
        status="healthy" if is_available else "degraded",
        llm_available=is_available,
        supported_types=[t.value for t in InterviewTypeEnum],
        supported_difficulties=[d.value for d in DifficultyLevelEnum],
    )
