"""
Unit tests for the InterviewCoachingService.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from backend.services.interview_service import (
    InterviewCoachingService,
    QuestionFeedback,
    SessionSummary,
)
from backend.models.interview import (
    InterviewSession,
    InterviewQuestion,
    InterviewType,
    DifficultyLevel,
)


class TestQuestionFeedback:
    """Tests for QuestionFeedback dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        feedback = QuestionFeedback(
            score=85,
            feedback="Great use of the STAR framework.",
            strengths=["Clear structure", "Quantified results"],
            improvements=["Add more context"],
            sample_answer="A strong response would include...",
        )

        result = feedback.to_dict()

        assert result["score"] == 85
        assert result["feedback"] == "Great use of the STAR framework."
        assert "Clear structure" in result["strengths"]
        assert "Add more context" in result["improvements"]
        assert result["sample_answer"] is not None

    def test_to_dict_with_defaults(self):
        """Test conversion with default values."""
        feedback = QuestionFeedback(
            score=50,
            feedback="Response recorded.",
        )

        result = feedback.to_dict()

        assert result["score"] == 50
        assert result["strengths"] == []
        assert result["improvements"] == []
        assert result["sample_answer"] is None


class TestSessionSummary:
    """Tests for SessionSummary dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        summary = SessionSummary(
            overall_score=75,
            total_questions=5,
            completed_questions=5,
            feedback_summary="Good performance overall.",
            strengths=["Leadership", "Communication"],
            areas_to_improve=["Technical depth"],
            recommendations=["Practice system design"],
        )

        result = summary.to_dict()

        assert result["overall_score"] == 75
        assert result["total_questions"] == 5
        assert result["completed_questions"] == 5
        assert result["feedback_summary"] == "Good performance overall."
        assert len(result["strengths"]) == 2
        assert len(result["areas_to_improve"]) == 1
        assert len(result["recommendations"]) == 1

    def test_to_dict_with_defaults(self):
        """Test conversion with default values."""
        summary = SessionSummary(
            overall_score=60,
            total_questions=3,
            completed_questions=2,
            feedback_summary="Session incomplete.",
        )

        result = summary.to_dict()

        assert result["strengths"] == []
        assert result["areas_to_improve"] == []
        assert result["recommendations"] == []


class TestInterviewType:
    """Tests for InterviewType enum."""

    def test_interview_type_values(self):
        """Test interview type enum values."""
        assert InterviewType.BEHAVIORAL.value == "behavioral"
        assert InterviewType.TECHNICAL.value == "technical"
        assert InterviewType.SYSTEM_DESIGN.value == "system_design"
        assert InterviewType.CASE_STUDY.value == "case_study"
        assert InterviewType.SITUATIONAL.value == "situational"
        assert InterviewType.COMPETENCY.value == "competency"

    def test_interview_type_from_string(self):
        """Test creating interview type from string."""
        assert InterviewType("behavioral") == InterviewType.BEHAVIORAL
        assert InterviewType("technical") == InterviewType.TECHNICAL


class TestDifficultyLevel:
    """Tests for DifficultyLevel enum."""

    def test_difficulty_level_values(self):
        """Test difficulty level enum values."""
        assert DifficultyLevel.ENTRY.value == "entry"
        assert DifficultyLevel.MID.value == "mid"
        assert DifficultyLevel.SENIOR.value == "senior"
        assert DifficultyLevel.LEAD.value == "lead"
        assert DifficultyLevel.EXECUTIVE.value == "executive"


class TestInterviewCoachingService:
    """Tests for InterviewCoachingService."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM service."""
        mock = MagicMock()

        async def mock_generate_structured(prompt: str, system_prompt: str = None) -> dict:
            # Return appropriate response based on prompt content
            if "Generate interview question" in prompt:
                return {
                    "question": "Tell me about a time when you demonstrated leadership.",
                    "category": "leadership",
                }
            elif "Evaluate this interview response" in prompt:
                return {
                    "score": 75,
                    "feedback": "Good use of the STAR framework with specific examples.",
                    "strengths": ["Clear structure", "Relevant example"],
                    "improvements": ["Add quantified results", "Be more concise"],
                    "sample_answer": "A strong response would start by setting context...",
                }
            elif "Generate a summary" in prompt:
                return {
                    "feedback_summary": "You demonstrated solid communication skills throughout the interview.",
                    "top_strengths": ["Leadership", "Communication", "Problem solving"],
                    "areas_to_improve": ["Technical specificity", "Time management"],
                    "recommendations": ["Practice with more technical questions", "Use more metrics"],
                }
            return {}

        mock.generate_structured = AsyncMock(side_effect=mock_generate_structured)
        mock.is_available = MagicMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.flush = AsyncMock()
        mock.refresh = AsyncMock()
        mock.commit = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def interview_service(self, mock_db, mock_llm):
        """Create interview service with mocked dependencies."""
        return InterviewCoachingService(db=mock_db, llm_service=mock_llm)

    def test_question_frameworks_defined(self, interview_service):
        """Test that question frameworks are defined for all types."""
        for interview_type in InterviewType:
            assert interview_type in interview_service.QUESTION_FRAMEWORKS
            assert len(interview_service.QUESTION_FRAMEWORKS[interview_type]) > 0

    def test_behavioral_categories_defined(self, interview_service):
        """Test that behavioral categories are defined."""
        assert len(interview_service.BEHAVIORAL_CATEGORIES) > 0
        assert "leadership" in interview_service.BEHAVIORAL_CATEGORIES
        assert "teamwork" in interview_service.BEHAVIORAL_CATEGORIES

    def test_technical_categories_defined(self, interview_service):
        """Test that technical categories are defined."""
        assert len(interview_service.TECHNICAL_CATEGORIES) > 0
        assert "coding" in interview_service.TECHNICAL_CATEGORIES
        assert "algorithms" in interview_service.TECHNICAL_CATEGORIES

    def test_system_prompt_defined(self, interview_service):
        """Test that system prompt is defined."""
        assert interview_service.SYSTEM_PROMPT
        assert "interview" in interview_service.SYSTEM_PROMPT.lower()
        assert "coach" in interview_service.SYSTEM_PROMPT.lower()

    def test_select_category_behavioral(self, interview_service):
        """Test category selection for behavioral interviews."""
        category1 = interview_service._select_category(InterviewType.BEHAVIORAL, 1)
        category2 = interview_service._select_category(InterviewType.BEHAVIORAL, 2)

        assert category1 in interview_service.BEHAVIORAL_CATEGORIES
        assert category2 in interview_service.BEHAVIORAL_CATEGORIES
        assert category1 != category2

    def test_select_category_technical(self, interview_service):
        """Test category selection for technical interviews."""
        category = interview_service._select_category(InterviewType.TECHNICAL, 1)
        assert category in interview_service.TECHNICAL_CATEGORIES

    def test_select_category_rotation(self, interview_service):
        """Test that categories rotate through the list."""
        categories = []
        for i in range(1, len(interview_service.BEHAVIORAL_CATEGORIES) + 2):
            cat = interview_service._select_category(InterviewType.BEHAVIORAL, i)
            categories.append(cat)

        # Should wrap around
        assert categories[0] == categories[len(interview_service.BEHAVIORAL_CATEGORIES)]

    def test_build_question_prompt_basic(self, interview_service):
        """Test building basic question prompt."""
        prompt = interview_service._build_question_prompt(
            interview_type=InterviewType.BEHAVIORAL,
            difficulty=DifficultyLevel.MID,
            target_role=None,
            target_company=None,
            focus_areas=[],
            category="leadership",
            question_number=1,
            total_questions=5,
            job_context=None,
        )

        assert "Generate interview question #1" in prompt
        assert "behavioral" in prompt
        assert "mid" in prompt
        assert "leadership" in prompt

    def test_build_question_prompt_with_context(self, interview_service):
        """Test building question prompt with full context."""
        prompt = interview_service._build_question_prompt(
            interview_type=InterviewType.TECHNICAL,
            difficulty=DifficultyLevel.SENIOR,
            target_role="Senior Software Engineer",
            target_company="Google",
            focus_areas=["system design", "scalability"],
            category="architecture",
            question_number=3,
            total_questions=5,
            job_context={
                "title": "Senior Backend Engineer",
                "skills": ["Python", "Kubernetes", "PostgreSQL"],
            },
        )

        assert "technical" in prompt
        assert "senior" in prompt
        assert "Senior Software Engineer" in prompt
        assert "Google" in prompt
        assert "system design" in prompt
        assert "Python" in prompt

    def test_get_fallback_question_behavioral(self, interview_service):
        """Test fallback questions for behavioral interviews."""
        question = interview_service._get_fallback_question(InterviewType.BEHAVIORAL, 1)
        assert len(question) > 0
        assert "?" in question or "Tell me" in question

    def test_get_fallback_question_technical(self, interview_service):
        """Test fallback questions for technical interviews."""
        question = interview_service._get_fallback_question(InterviewType.TECHNICAL, 1)
        assert len(question) > 0

    def test_get_fallback_question_system_design(self, interview_service):
        """Test fallback questions for system design interviews."""
        question = interview_service._get_fallback_question(InterviewType.SYSTEM_DESIGN, 1)
        assert len(question) > 0
        assert "design" in question.lower() or "would you" in question.lower()

    def test_get_fallback_question_rotation(self, interview_service):
        """Test that fallback questions rotate."""
        q1 = interview_service._get_fallback_question(InterviewType.BEHAVIORAL, 1)
        q2 = interview_service._get_fallback_question(InterviewType.BEHAVIORAL, 2)
        q6 = interview_service._get_fallback_question(InterviewType.BEHAVIORAL, 6)

        assert q1 != q2
        assert q1 == q6  # Should wrap around after 5 questions

    def test_format_questions_for_summary_empty(self, interview_service):
        """Test formatting empty question list."""
        result = interview_service._format_questions_for_summary([])
        assert result == "No scored questions"

    def test_format_questions_for_summary_with_questions(self, interview_service):
        """Test formatting questions for summary."""
        q1 = MagicMock()
        q1.question_order = 1
        q1.question_category = "leadership"
        q1.score = 80

        q2 = MagicMock()
        q2.question_order = 2
        q2.question_category = "teamwork"
        q2.score = 75

        result = interview_service._format_questions_for_summary([q1, q2])

        assert "Q1" in result
        assert "Q2" in result
        assert "leadership" in result
        assert "80/100" in result
        assert "75/100" in result

    def test_format_questions_for_summary_no_score(self, interview_service):
        """Test formatting questions without scores."""
        q1 = MagicMock()
        q1.question_order = 1
        q1.question_category = "leadership"
        q1.score = None

        result = interview_service._format_questions_for_summary([q1])
        assert result == "No scored questions"


class TestInterviewCoachingServiceAsync:
    """Async tests for InterviewCoachingService."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM service."""
        mock = MagicMock()

        async def mock_generate_structured(prompt: str, system_prompt: str = None) -> dict:
            if "Generate interview question" in prompt:
                return {
                    "question": "Tell me about a time when you demonstrated leadership.",
                    "category": "leadership",
                }
            elif "Evaluate this interview response" in prompt:
                return {
                    "score": 75,
                    "feedback": "Good use of the STAR framework.",
                    "strengths": ["Clear structure"],
                    "improvements": ["Add metrics"],
                    "sample_answer": "Example response...",
                }
            elif "summary" in prompt.lower():
                return {
                    "feedback_summary": "Good performance overall.",
                    "top_strengths": ["Communication"],
                    "areas_to_improve": ["Technical depth"],
                    "recommendations": ["Practice more"],
                }
            return {}

        mock.generate_structured = AsyncMock(side_effect=mock_generate_structured)
        return mock

    @pytest.mark.asyncio
    async def test_create_session(self, db_session, mock_llm, user_factory):
        """Test creating an interview session."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(
            user_id=user.id,
            interview_type=InterviewType.BEHAVIORAL,
            difficulty=DifficultyLevel.MID,
            target_role="Software Engineer",
            target_company="TechCorp",
            total_questions=5,
        )

        assert session.user_id == user.id
        assert session.interview_type == InterviewType.BEHAVIORAL
        assert session.difficulty == DifficultyLevel.MID
        assert session.target_role == "Software Engineer"
        assert session.target_company == "TechCorp"
        assert session.total_questions == 5
        assert session.completed_questions == 0

        # Re-fetch session with relationships loaded to verify question was created
        loaded_session = await service.get_session(session.id)
        assert len(loaded_session.questions) == 1  # First question generated

    @pytest.mark.asyncio
    async def test_create_session_with_focus_areas(self, db_session, mock_llm, user_factory):
        """Test creating session with specific focus areas."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(
            user_id=user.id,
            interview_type=InterviewType.TECHNICAL,
            difficulty=DifficultyLevel.SENIOR,
            focus_areas=["system design", "algorithms"],
            total_questions=3,
        )

        assert session.focus_areas == ["system design", "algorithms"]
        assert session.interview_type == InterviewType.TECHNICAL

    @pytest.mark.asyncio
    async def test_get_session(self, db_session, mock_llm, user_factory):
        """Test getting a session by ID."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        created = await service.create_session(
            user_id=user.id,
            interview_type=InterviewType.BEHAVIORAL,
        )
        await db_session.commit()

        fetched = await service.get_session(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, db_session, mock_llm):
        """Test getting a non-existent session."""
        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        result = await service.get_session(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, db_session, mock_llm, user_factory):
        """Test getting sessions for a user."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        # Create multiple sessions
        await service.create_session(user_id=user.id, interview_type=InterviewType.BEHAVIORAL)
        await service.create_session(user_id=user.id, interview_type=InterviewType.TECHNICAL)
        await db_session.commit()

        sessions = await service.get_user_sessions(user_id=user.id)

        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_get_user_sessions_with_limit(self, db_session, mock_llm, user_factory):
        """Test getting sessions with limit."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        for _ in range(5):
            await service.create_session(user_id=user.id)
        await db_session.commit()

        sessions = await service.get_user_sessions(user_id=user.id, limit=3)

        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_get_current_question(self, db_session, mock_llm, user_factory):
        """Test getting current unanswered question."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(user_id=user.id)
        await db_session.commit()

        question = await service.get_current_question(session.id)

        assert question is not None
        assert question.session_id == session.id
        assert question.user_response is None
        assert question.question_order == 1

    @pytest.mark.asyncio
    async def test_submit_response(self, db_session, mock_llm, user_factory):
        """Test submitting a response to a question."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(user_id=user.id, total_questions=3)
        await db_session.commit()

        question = await service.get_current_question(session.id)

        feedback = await service.submit_response(
            question_id=question.id,
            response="I led a project where we migrated to microservices. I coordinated 5 engineers and we delivered 2 weeks early.",
            response_duration_seconds=180,
        )

        assert isinstance(feedback, QuestionFeedback)
        assert 0 <= feedback.score <= 100
        assert len(feedback.feedback) > 0

        # Verify question was updated
        await db_session.refresh(question)
        assert question.user_response is not None
        assert question.answered_at is not None
        assert question.score is not None

    @pytest.mark.asyncio
    async def test_submit_response_generates_next_question(self, db_session, mock_llm, user_factory):
        """Test that submitting response generates next question."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(user_id=user.id, total_questions=3)
        await db_session.commit()

        q1 = await service.get_current_question(session.id)
        await service.submit_response(question_id=q1.id, response="My response")
        await db_session.commit()

        q2 = await service.get_current_question(session.id)

        assert q2 is not None
        assert q2.question_order == 2
        assert q2.id != q1.id

    @pytest.mark.asyncio
    async def test_submit_response_already_answered(self, db_session, mock_llm, user_factory):
        """Test that submitting to answered question raises error."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(user_id=user.id)
        await db_session.commit()

        question = await service.get_current_question(session.id)
        await service.submit_response(question_id=question.id, response="First response")
        await db_session.commit()

        with pytest.raises(ValueError, match="already answered"):
            await service.submit_response(question_id=question.id, response="Second response")

    @pytest.mark.asyncio
    async def test_submit_response_invalid_question(self, db_session, mock_llm):
        """Test that submitting to non-existent question raises error."""
        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        with pytest.raises(ValueError, match="not found"):
            await service.submit_response(question_id=uuid4(), response="Response")

    @pytest.mark.asyncio
    async def test_complete_session(self, db_session, mock_llm, user_factory):
        """Test completing a session."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(user_id=user.id, total_questions=2)
        await db_session.commit()

        # Answer all questions
        for _ in range(2):
            q = await service.get_current_question(session.id)
            if q:
                await service.submit_response(question_id=q.id, response="My response")
        await db_session.commit()

        summary = await service.complete_session(session.id)

        assert isinstance(summary, SessionSummary)
        assert summary.total_questions == 2
        assert summary.completed_questions == 2
        assert 0 <= summary.overall_score <= 100
        assert len(summary.feedback_summary) > 0

    @pytest.mark.asyncio
    async def test_complete_session_not_found(self, db_session, mock_llm):
        """Test completing non-existent session raises error."""
        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        with pytest.raises(ValueError, match="not found"):
            await service.complete_session(uuid4())

    @pytest.mark.asyncio
    async def test_complete_session_already_completed(self, db_session, mock_llm, user_factory):
        """Test completing already completed session raises error."""
        user = await user_factory()
        await db_session.commit()

        service = InterviewCoachingService(db=db_session, llm_service=mock_llm)

        session = await service.create_session(user_id=user.id, total_questions=1)
        await db_session.commit()

        q = await service.get_current_question(session.id)
        await service.submit_response(question_id=q.id, response="Response")
        await db_session.commit()

        await service.complete_session(session.id)
        await db_session.commit()

        with pytest.raises(ValueError, match="already completed"):
            await service.complete_session(session.id)
