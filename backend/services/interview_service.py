"""Interview Coaching Service - AI-powered interview practice and feedback."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.models.interview import (
    InterviewSession,
    InterviewQuestion,
    InterviewType,
    DifficultyLevel,
)
from backend.models.job import Job
from backend.models.resume import Resume
from backend.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


@dataclass
class QuestionFeedback:
    """Feedback for a single interview question response."""

    score: int  # 0-100
    feedback: str
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    sample_answer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "feedback": self.feedback,
            "strengths": self.strengths,
            "improvements": self.improvements,
            "sample_answer": self.sample_answer,
        }


@dataclass
class SessionSummary:
    """Summary of a completed interview session."""

    overall_score: int
    total_questions: int
    completed_questions: int
    feedback_summary: str
    strengths: List[str] = field(default_factory=list)
    areas_to_improve: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_score": self.overall_score,
            "total_questions": self.total_questions,
            "completed_questions": self.completed_questions,
            "feedback_summary": self.feedback_summary,
            "strengths": self.strengths,
            "areas_to_improve": self.areas_to_improve,
            "recommendations": self.recommendations,
        }


class InterviewCoachingService:
    """Service for AI-powered interview coaching and practice."""

    QUESTION_FRAMEWORKS = {
        InterviewType.BEHAVIORAL: "STAR (Situation, Task, Action, Result)",
        InterviewType.TECHNICAL: "Problem-Approach-Solution-Complexity",
        InterviewType.SYSTEM_DESIGN: "Requirements-Architecture-Tradeoffs-Scalability",
        InterviewType.CASE_STUDY: "Framework-Analysis-Recommendation-Implementation",
        InterviewType.SITUATIONAL: "STAR (Situation, Task, Action, Result)",
        InterviewType.COMPETENCY: "CAR (Context, Action, Result)",
    }

    BEHAVIORAL_CATEGORIES = [
        "leadership",
        "teamwork",
        "conflict_resolution",
        "problem_solving",
        "communication",
        "adaptability",
        "time_management",
        "decision_making",
        "initiative",
        "customer_focus",
    ]

    TECHNICAL_CATEGORIES = [
        "coding",
        "algorithms",
        "data_structures",
        "debugging",
        "optimization",
        "architecture",
        "testing",
        "security",
    ]

    SYSTEM_PROMPT = """You are an expert interview coach with extensive experience in hiring and career development.
Your role is to:
- Generate realistic interview questions tailored to the role and company
- Provide constructive, actionable feedback on responses
- Help candidates improve their interview skills
- Be encouraging while being honest about areas for improvement

When evaluating responses:
- Check for the appropriate framework usage (STAR, CAR, etc.)
- Assess specificity and concreteness of examples
- Evaluate communication clarity and structure
- Consider relevance to the question asked
- Look for quantified results and impact"""

    def __init__(
        self,
        db: AsyncSession,
        llm_service: Optional[LLMService] = None,
    ):
        """Initialize interview coaching service.

        Args:
            db: Database session for persisting sessions.
            llm_service: Optional LLM service instance.
        """
        self.db = db
        self.llm = llm_service or get_llm_service()

    async def create_session(
        self,
        user_id: UUID,
        interview_type: InterviewType = InterviewType.BEHAVIORAL,
        difficulty: DifficultyLevel = DifficultyLevel.MID,
        job_id: Optional[UUID] = None,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        focus_areas: Optional[List[str]] = None,
        total_questions: int = 5,
    ) -> InterviewSession:
        """Create a new interview practice session.

        Args:
            user_id: User ID.
            interview_type: Type of interview practice.
            difficulty: Difficulty level.
            job_id: Optional job ID to tailor questions.
            target_role: Target job role.
            target_company: Target company name.
            focus_areas: Specific areas to focus on.
            total_questions: Number of questions in session.

        Returns:
            Created InterviewSession with first question generated.
        """
        logger.info(f"Creating interview session for user {user_id}")

        # Get job context if provided
        job_context = None
        if job_id:
            job = await self._get_job(job_id)
            if job:
                job_context = {
                    "title": job.title,
                    "company": job.company,
                    "skills": job.skills or [],
                    "description": job.description,
                }
                target_role = target_role or job.title
                target_company = target_company or job.company

        # Create session
        session = InterviewSession(
            user_id=user_id,
            job_id=job_id,
            interview_type=interview_type,
            difficulty=difficulty,
            target_role=target_role,
            target_company=target_company,
            focus_areas=focus_areas or [],
            total_questions=total_questions,
            completed_questions=0,
        )
        self.db.add(session)
        await self.db.flush()

        # Generate first question
        await self._generate_question(
            session=session,
            question_order=1,
            job_context=job_context,
        )

        await self.db.refresh(session)
        return session

    async def generate_all_session_questions(
        self,
        session: InterviewSession,
        job_context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Generate all remaining questions for a session upfront.

        Args:
            session: The interview session.
            job_context: Optional job context for tailoring.

        Returns:
            Number of questions generated.
        """
        # Get current question count
        result = await self.db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session.id)
        )
        existing_questions = len(result.scalars().all())

        questions_generated = 0
        for i in range(existing_questions + 1, session.total_questions + 1):
            await self._generate_question(
                session=session,
                question_order=i,
                job_context=job_context,
            )
            questions_generated += 1

        return questions_generated

    async def get_session(self, session_id: UUID) -> Optional[InterviewSession]:
        """Get an interview session by ID.

        Args:
            session_id: Session UUID.

        Returns:
            InterviewSession if found, None otherwise.
        """
        result = await self.db.execute(
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(selectinload(InterviewSession.questions))
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        user_id: UUID,
        limit: int = 10,
        include_completed: bool = True,
    ) -> List[InterviewSession]:
        """Get interview sessions for a user.

        Args:
            user_id: User ID.
            limit: Maximum sessions to return.
            include_completed: Whether to include completed sessions.

        Returns:
            List of InterviewSessions.
        """
        query = (
            select(InterviewSession)
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.created_at.desc())
            .limit(limit)
        )

        if not include_completed:
            query = query.where(InterviewSession.completed_at.is_(None))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_current_question(
        self, session_id: UUID
    ) -> Optional[InterviewQuestion]:
        """Get the current unanswered question in a session.

        Args:
            session_id: Session UUID.

        Returns:
            Current InterviewQuestion or None if session complete.
        """
        result = await self.db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .where(InterviewQuestion.user_response.is_(None))
            .order_by(InterviewQuestion.question_order)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def submit_response(
        self,
        question_id: UUID,
        response: str,
        response_duration_seconds: Optional[int] = None,
    ) -> QuestionFeedback:
        """Submit a response to an interview question and get feedback.

        Args:
            question_id: Question UUID.
            response: User's response text.
            response_duration_seconds: Time taken to respond.

        Returns:
            QuestionFeedback with score and analysis.
        """
        # Get the question
        result = await self.db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.id == question_id)
            .options(selectinload(InterviewQuestion.session))
        )
        question = result.scalar_one_or_none()

        if not question:
            raise ValueError("Question not found")

        if question.user_response:
            raise ValueError("Question already answered")

        # Store the response
        question.user_response = response
        question.response_duration_seconds = response_duration_seconds
        question.answered_at = datetime.utcnow()

        # Generate AI feedback
        feedback = await self._evaluate_response(question)

        # Apply feedback to question
        question.feedback = feedback.feedback
        question.score = feedback.score
        question.strengths = feedback.strengths
        question.improvements = feedback.improvements
        question.sample_answer = feedback.sample_answer

        # Update session progress
        session = question.session
        session.completed_questions += 1

        # Generate next question if session not complete
        if session.completed_questions < session.total_questions:
            await self._generate_question(
                session=session,
                question_order=session.completed_questions + 1,
            )

        await self.db.flush()
        return feedback

    async def complete_session(self, session_id: UUID) -> SessionSummary:
        """Complete an interview session and generate summary.

        Args:
            session_id: Session UUID.

        Returns:
            SessionSummary with overall feedback.
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        if session.completed_at:
            raise ValueError("Session already completed")

        # Generate summary
        summary = await self._generate_session_summary(session)

        # Update session
        session.completed_at = datetime.utcnow()
        session.overall_score = summary.overall_score
        session.feedback_summary = summary.feedback_summary

        await self.db.flush()
        return summary

    async def _generate_question(
        self,
        session: InterviewSession,
        question_order: int,
        job_context: Optional[Dict[str, Any]] = None,
    ) -> InterviewQuestion:
        """Generate a new interview question.

        Args:
            session: The interview session.
            question_order: Position of this question (1-indexed).
            job_context: Optional job context for tailoring.

        Returns:
            Generated InterviewQuestion.
        """
        # Determine category based on interview type
        category = self._select_category(session.interview_type, question_order)

        # Build generation prompt
        prompt = self._build_question_prompt(
            interview_type=session.interview_type,
            difficulty=session.difficulty,
            target_role=session.target_role,
            target_company=session.target_company,
            focus_areas=session.focus_areas or [],
            category=category,
            question_number=question_order,
            total_questions=session.total_questions,
            job_context=job_context,
        )

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
            )

            question_text = result.get("question", "Tell me about yourself.")
            question_category = result.get("category", category)

        except Exception as e:
            logger.error(f"Failed to generate question: {e}")
            # Fallback question
            question_text = self._get_fallback_question(
                session.interview_type, question_order
            )
            question_category = category

        # Create question
        question = InterviewQuestion(
            session_id=session.id,
            question_order=question_order,
            question_text=question_text,
            question_category=question_category,
            expected_framework=self.QUESTION_FRAMEWORKS.get(session.interview_type),
        )
        self.db.add(question)
        await self.db.flush()

        return question

    async def _evaluate_response(
        self, question: InterviewQuestion
    ) -> QuestionFeedback:
        """Evaluate a user's response with AI.

        Args:
            question: The question with user response.

        Returns:
            QuestionFeedback with detailed analysis.
        """
        session = question.session

        prompt = f"""Evaluate this interview response.

INTERVIEW TYPE: {session.interview_type.value}
DIFFICULTY: {session.difficulty.value}
TARGET ROLE: {session.target_role or 'General'}

QUESTION:
{question.question_text}

EXPECTED FRAMEWORK: {question.expected_framework or 'Any structured approach'}

CANDIDATE'S RESPONSE:
{question.user_response}

Provide evaluation as JSON:
{{
    "score": <0-100 integer>,
    "feedback": "<2-3 sentence overall assessment>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "improvements": ["<improvement 1>", "<improvement 2>"],
    "sample_answer": "<brief example of an excellent response for this question>"
}}

SCORING CRITERIA:
- 90-100: Excellent - Strong structure, specific examples, quantified results
- 70-89: Good - Clear structure, relevant examples, some specifics
- 50-69: Fair - Basic structure, generic examples, lacks detail
- 30-49: Needs Work - Weak structure, vague or missing examples
- 0-29: Poor - No structure, off-topic or minimal response"""

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
            )

            return QuestionFeedback(
                score=min(100, max(0, int(result.get("score", 50)))),
                feedback=result.get("feedback", "Response recorded."),
                strengths=result.get("strengths", []),
                improvements=result.get("improvements", []),
                sample_answer=result.get("sample_answer"),
            )

        except Exception as e:
            logger.error(f"Failed to evaluate response: {e}")
            # Return default feedback
            return QuestionFeedback(
                score=50,
                feedback="Your response has been recorded. Consider using the STAR framework for behavioral questions.",
                strengths=["Response provided"],
                improvements=["Add more specific examples"],
            )

    async def _generate_session_summary(
        self, session: InterviewSession
    ) -> SessionSummary:
        """Generate a summary for a completed session.

        Args:
            session: The interview session.

        Returns:
            SessionSummary with overall assessment.
        """
        # Calculate average score
        scores = [q.score for q in session.questions if q.score is not None]
        avg_score = int(sum(scores) / len(scores)) if scores else 0

        # Collect all feedback
        all_strengths = []
        all_improvements = []
        for q in session.questions:
            if q.strengths:
                all_strengths.extend(q.strengths)
            if q.improvements:
                all_improvements.extend(q.improvements)

        prompt = f"""Generate a summary for this completed interview practice session.

INTERVIEW TYPE: {session.interview_type.value}
DIFFICULTY: {session.difficulty.value}
TARGET ROLE: {session.target_role or 'General'}
QUESTIONS COMPLETED: {session.completed_questions}/{session.total_questions}
AVERAGE SCORE: {avg_score}

INDIVIDUAL QUESTION PERFORMANCE:
{self._format_questions_for_summary(session.questions)}

IDENTIFIED STRENGTHS (from individual questions):
{', '.join(set(all_strengths[:10])) if all_strengths else 'None identified'}

IDENTIFIED IMPROVEMENTS (from individual questions):
{', '.join(set(all_improvements[:10])) if all_improvements else 'None identified'}

Provide summary as JSON:
{{
    "feedback_summary": "<2-3 paragraph overall assessment and encouragement>",
    "top_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "areas_to_improve": ["<area 1>", "<area 2>", "<area 3>"],
    "recommendations": ["<actionable recommendation 1>", "<actionable recommendation 2>"]
}}"""

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
            )

            return SessionSummary(
                overall_score=avg_score,
                total_questions=session.total_questions,
                completed_questions=session.completed_questions,
                feedback_summary=result.get(
                    "feedback_summary",
                    f"You completed {session.completed_questions} questions with an average score of {avg_score}.",
                ),
                strengths=result.get("top_strengths", []),
                areas_to_improve=result.get("areas_to_improve", []),
                recommendations=result.get("recommendations", []),
            )

        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            return SessionSummary(
                overall_score=avg_score,
                total_questions=session.total_questions,
                completed_questions=session.completed_questions,
                feedback_summary=f"Session completed with {session.completed_questions} questions answered. Average score: {avg_score}%.",
                strengths=list(set(all_strengths[:3])),
                areas_to_improve=list(set(all_improvements[:3])),
                recommendations=["Practice with more questions to improve consistency."],
            )

    def _select_category(
        self, interview_type: InterviewType, question_order: int
    ) -> str:
        """Select a question category based on type and order."""
        if interview_type == InterviewType.BEHAVIORAL:
            categories = self.BEHAVIORAL_CATEGORIES
        elif interview_type == InterviewType.TECHNICAL:
            categories = self.TECHNICAL_CATEGORIES
        else:
            categories = self.BEHAVIORAL_CATEGORIES

        # Rotate through categories
        index = (question_order - 1) % len(categories)
        return categories[index]

    def _build_question_prompt(
        self,
        interview_type: InterviewType,
        difficulty: DifficultyLevel,
        target_role: Optional[str],
        target_company: Optional[str],
        focus_areas: List[str],
        category: str,
        question_number: int,
        total_questions: int,
        job_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for question generation."""
        prompt_parts = [
            f"Generate interview question #{question_number} of {total_questions}.",
            "",
            f"INTERVIEW TYPE: {interview_type.value}",
            f"DIFFICULTY: {difficulty.value}",
            f"CATEGORY: {category}",
        ]

        if target_role:
            prompt_parts.append(f"TARGET ROLE: {target_role}")
        if target_company:
            prompt_parts.append(f"TARGET COMPANY: {target_company}")
        if focus_areas:
            prompt_parts.append(f"FOCUS AREAS: {', '.join(focus_areas)}")

        if job_context:
            prompt_parts.extend([
                "",
                "JOB CONTEXT:",
                f"Title: {job_context.get('title', 'Unknown')}",
                f"Skills: {', '.join(job_context.get('skills', [])[:10])}",
            ])

        prompt_parts.extend([
            "",
            "Generate a realistic interview question for this context.",
            "",
            "Return JSON:",
            '{',
            '    "question": "<the interview question>",',
            '    "category": "<category like leadership, coding, etc>"',
            '}',
        ])

        return "\n".join(prompt_parts)

    def _get_fallback_question(
        self, interview_type: InterviewType, question_order: int
    ) -> str:
        """Get a fallback question if generation fails."""
        fallback_questions = {
            InterviewType.BEHAVIORAL: [
                "Tell me about a time when you had to overcome a significant challenge at work.",
                "Describe a situation where you had to work with a difficult team member.",
                "Give an example of when you showed initiative in your role.",
                "Tell me about a time you failed and what you learned from it.",
                "Describe your most significant professional achievement.",
            ],
            InterviewType.TECHNICAL: [
                "Explain your approach to debugging a complex issue in production.",
                "How would you design a scalable API for a high-traffic application?",
                "What's your experience with testing strategies and code quality?",
                "Describe a technical decision you made that had significant impact.",
                "How do you stay current with technology trends in your field?",
            ],
            InterviewType.SYSTEM_DESIGN: [
                "How would you design a URL shortening service?",
                "Design a real-time chat application that scales to millions of users.",
                "How would you build a recommendation system?",
                "Design a distributed file storage system.",
                "How would you architect a payment processing system?",
            ],
        }

        questions = fallback_questions.get(
            interview_type, fallback_questions[InterviewType.BEHAVIORAL]
        )
        index = (question_order - 1) % len(questions)
        return questions[index]

    def _format_questions_for_summary(
        self, questions: List[InterviewQuestion]
    ) -> str:
        """Format questions for summary prompt."""
        lines = []
        for q in questions:
            if q.score is not None:
                lines.append(
                    f"Q{q.question_order}: {q.question_category or 'general'} - Score: {q.score}/100"
                )
        return "\n".join(lines) if lines else "No scored questions"

    async def _get_job(self, job_id: UUID) -> Optional[Job]:
        """Fetch job from database."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()


# Convenience functions
async def create_interview_session(
    db: AsyncSession,
    user_id: UUID,
    interview_type: InterviewType = InterviewType.BEHAVIORAL,
    **kwargs,
) -> InterviewSession:
    """Create a new interview practice session."""
    service = InterviewCoachingService(db)
    return await service.create_session(user_id, interview_type, **kwargs)


async def get_interview_session(
    db: AsyncSession, session_id: UUID
) -> Optional[InterviewSession]:
    """Get an interview session by ID."""
    service = InterviewCoachingService(db)
    return await service.get_session(session_id)
