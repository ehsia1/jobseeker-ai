"""Feedback collection service for ML learning loop."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from backend.models.feedback import UserFeedback
from backend.models.job import Job, JobMatch
from backend.models.recommendation import UserPreferenceModel, RecommendationLog

logger = logging.getLogger(__name__)


class FeedbackCollectionService:
    """Service for collecting and analyzing user feedback for ML."""

    # Valid feedback actions
    VALID_ACTIONS = {
        "viewed",
        "clicked",
        "saved",
        "applied",
        "rejected",
        "interviewed",
        "hired",
    }

    # Engagement weights for ML training
    ENGAGEMENT_WEIGHTS = {
        "viewed": 0.1,
        "clicked": 0.2,
        "saved": 0.5,
        "applied": 1.0,
        "rejected": -0.5,
        "interviewed": 2.0,
        "hired": 3.0,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_feedback(
        self,
        user_id: UUID,
        job_id: UUID,
        match_id: UUID,
        action: str,
        feedback_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserFeedback:
        """
        Record user feedback for a job match.

        Args:
            user_id: User ID
            job_id: Job ID
            match_id: JobMatch ID
            action: Action taken (viewed, clicked, saved, applied, rejected, etc.)
            feedback_text: Optional text feedback from user
            metadata: Optional additional context

        Returns:
            Created UserFeedback object
        """
        if action not in self.VALID_ACTIONS:
            raise ValueError(f"Invalid action: {action}. Must be one of {self.VALID_ACTIONS}")

        # Classify feedback type
        if action in {"saved", "applied", "interviewed", "hired"}:
            feedback_type = "positive"
        elif action in {"rejected"}:
            feedback_type = "negative"
        else:
            feedback_type = "neutral"

        feedback = UserFeedback(
            user_id=user_id,
            job_id=job_id,
            match_id=match_id,
            action=action,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            feedback_metadata=metadata or {},
        )

        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)

        logger.info(f"Recorded {action} feedback for user {user_id} on job {job_id}")

        # Update recommendation log if exists
        await self._update_recommendation_log(user_id, job_id, action)

        return feedback

    async def _update_recommendation_log(
        self,
        user_id: UUID,
        job_id: UUID,
        action: str,
    ) -> None:
        """Update recommendation log with outcome."""
        result = await self.db.execute(
            select(RecommendationLog)
            .where(
                and_(
                    RecommendationLog.user_id == user_id,
                    RecommendationLog.job_id == job_id,
                )
            )
            .order_by(desc(RecommendationLog.created_at))
            .limit(1)
        )
        rec_log = result.scalar_one_or_none()

        if rec_log:
            if action == "viewed":
                rec_log.was_viewed = True
            elif action == "clicked":
                rec_log.was_clicked = True
            elif action == "saved":
                rec_log.was_saved = True
            elif action == "applied":
                rec_log.was_applied = True
            elif action == "rejected":
                rec_log.was_rejected = True

            rec_log.outcome_recorded_at = datetime.utcnow()
            await self.db.commit()

    async def get_user_feedback_history(
        self,
        user_id: UUID,
        days_back: int = 30,
        limit: int = 100,
    ) -> List[UserFeedback]:
        """
        Get user's feedback history.

        Args:
            user_id: User ID
            days_back: Number of days to look back
            limit: Maximum number of feedback entries

        Returns:
            List of UserFeedback objects
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        result = await self.db.execute(
            select(UserFeedback)
            .where(
                and_(
                    UserFeedback.user_id == user_id,
                    UserFeedback.created_at >= cutoff_date,
                )
            )
            .order_by(desc(UserFeedback.created_at))
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_feedback_statistics(
        self,
        user_id: UUID,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Get aggregated feedback statistics for a user.

        Args:
            user_id: User ID
            days_back: Number of days to look back

        Returns:
            Dictionary with feedback statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get action counts
        result = await self.db.execute(
            select(
                UserFeedback.action,
                func.count(UserFeedback.id).label("count"),
            )
            .where(
                and_(
                    UserFeedback.user_id == user_id,
                    UserFeedback.created_at >= cutoff_date,
                )
            )
            .group_by(UserFeedback.action)
        )

        action_counts = {row[0]: row[1] for row in result.all()}

        # Calculate engagement score
        total_engagement = sum(
            count * self.ENGAGEMENT_WEIGHTS.get(action, 0)
            for action, count in action_counts.items()
        )

        # Get positive/negative ratio
        positive_count = sum(
            count for action, count in action_counts.items()
            if action in {"saved", "applied", "interviewed", "hired"}
        )
        negative_count = action_counts.get("rejected", 0)

        return {
            "action_counts": action_counts,
            "total_interactions": sum(action_counts.values()),
            "total_engagement_score": total_engagement,
            "positive_actions": positive_count,
            "negative_actions": negative_count,
            "engagement_ratio": (
                positive_count / max(1, positive_count + negative_count)
            ),
            "days_analyzed": days_back,
        }

    async def get_training_samples(
        self,
        user_id: UUID,
        min_samples: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get training samples for ML model from user feedback.

        Args:
            user_id: User ID
            min_samples: Minimum samples required

        Returns:
            Dictionary with positive and negative samples
        """
        # Get positive feedback (saved, applied, interviewed, hired)
        positive_result = await self.db.execute(
            select(UserFeedback, Job)
            .join(Job, UserFeedback.job_id == Job.id)
            .where(
                and_(
                    UserFeedback.user_id == user_id,
                    UserFeedback.action.in_(["saved", "applied", "interviewed", "hired"]),
                )
            )
            .order_by(desc(UserFeedback.created_at))
        )

        positive_samples = []
        for feedback, job in positive_result.all():
            positive_samples.append({
                "job_id": str(job.id),
                "job_title": job.title,
                "skills": job.skills or [],
                "company": job.company,
                "remote": job.remote,
                "rate_min": float(job.rate_min) if job.rate_min else None,
                "rate_max": float(job.rate_max) if job.rate_max else None,
                "action": feedback.action,
                "weight": self.ENGAGEMENT_WEIGHTS.get(feedback.action, 0),
            })

        # Get negative feedback (rejected)
        negative_result = await self.db.execute(
            select(UserFeedback, Job)
            .join(Job, UserFeedback.job_id == Job.id)
            .where(
                and_(
                    UserFeedback.user_id == user_id,
                    UserFeedback.action == "rejected",
                )
            )
            .order_by(desc(UserFeedback.created_at))
        )

        negative_samples = []
        for feedback, job in negative_result.all():
            negative_samples.append({
                "job_id": str(job.id),
                "job_title": job.title,
                "skills": job.skills or [],
                "company": job.company,
                "remote": job.remote,
                "rate_min": float(job.rate_min) if job.rate_min else None,
                "rate_max": float(job.rate_max) if job.rate_max else None,
                "action": feedback.action,
                "weight": self.ENGAGEMENT_WEIGHTS.get(feedback.action, 0),
            })

        return {
            "positive_samples": positive_samples,
            "negative_samples": negative_samples,
            "total_samples": len(positive_samples) + len(negative_samples),
            "has_sufficient_data": (
                len(positive_samples) + len(negative_samples) >= min_samples
                and len(positive_samples) >= 3
            ),
        }

    async def analyze_skill_preferences(
        self,
        user_id: UUID,
    ) -> Dict[str, float]:
        """
        Analyze which skills the user prefers based on feedback.

        Args:
            user_id: User ID

        Returns:
            Dictionary mapping skills to preference scores
        """
        samples = await self.get_training_samples(user_id)

        skill_scores: Dict[str, Dict[str, float]] = {}

        # Process positive samples
        for sample in samples["positive_samples"]:
            weight = sample["weight"]
            for skill in sample["skills"]:
                skill_lower = skill.lower()
                if skill_lower not in skill_scores:
                    skill_scores[skill_lower] = {"positive": 0, "negative": 0}
                skill_scores[skill_lower]["positive"] += weight

        # Process negative samples
        for sample in samples["negative_samples"]:
            weight = abs(sample["weight"])
            for skill in sample["skills"]:
                skill_lower = skill.lower()
                if skill_lower not in skill_scores:
                    skill_scores[skill_lower] = {"positive": 0, "negative": 0}
                skill_scores[skill_lower]["negative"] += weight

        # Calculate net preference score for each skill
        preferences = {}
        for skill, scores in skill_scores.items():
            total = scores["positive"] + scores["negative"]
            if total > 0:
                # Normalize to -1 to 1 range
                preferences[skill] = (scores["positive"] - scores["negative"]) / total

        return preferences

    async def analyze_company_preferences(
        self,
        user_id: UUID,
    ) -> Dict[str, float]:
        """
        Analyze which companies the user prefers based on feedback.

        Args:
            user_id: User ID

        Returns:
            Dictionary mapping companies to preference scores
        """
        samples = await self.get_training_samples(user_id)

        company_scores: Dict[str, Dict[str, float]] = {}

        # Process samples
        for sample in samples["positive_samples"]:
            company = sample["company"]
            if company:
                company_lower = company.lower()
                if company_lower not in company_scores:
                    company_scores[company_lower] = {"positive": 0, "negative": 0}
                company_scores[company_lower]["positive"] += sample["weight"]

        for sample in samples["negative_samples"]:
            company = sample["company"]
            if company:
                company_lower = company.lower()
                if company_lower not in company_scores:
                    company_scores[company_lower] = {"positive": 0, "negative": 0}
                company_scores[company_lower]["negative"] += abs(sample["weight"])

        # Calculate net preference score
        preferences = {}
        for company, scores in company_scores.items():
            total = scores["positive"] + scores["negative"]
            if total > 0:
                preferences[company] = (scores["positive"] - scores["negative"]) / total

        return preferences

    async def get_implicit_preferences(
        self,
        user_id: UUID,
    ) -> Dict[str, float]:
        """
        Analyze implicit preferences from user behavior.

        Args:
            user_id: User ID

        Returns:
            Dictionary of implicit preferences
        """
        samples = await self.get_training_samples(user_id)

        # Calculate remote preference
        remote_positive = sum(
            1 for s in samples["positive_samples"] if s.get("remote")
        )
        remote_negative = sum(
            1 for s in samples["negative_samples"] if s.get("remote")
        )
        total_remote = remote_positive + remote_negative

        # Calculate compensation preference (prefers higher pay)
        positive_rates = [
            s["rate_max"] or s["rate_min"]
            for s in samples["positive_samples"]
            if s["rate_max"] or s["rate_min"]
        ]
        negative_rates = [
            s["rate_max"] or s["rate_min"]
            for s in samples["negative_samples"]
            if s["rate_max"] or s["rate_min"]
        ]

        preferences = {}

        # Remote preference
        if total_remote > 0:
            preferences["prefers_remote"] = remote_positive / total_remote

        # High pay preference
        if positive_rates and negative_rates:
            avg_positive_rate = sum(positive_rates) / len(positive_rates)
            avg_negative_rate = sum(negative_rates) / len(negative_rates)
            if avg_positive_rate > avg_negative_rate * 1.1:  # 10% higher
                preferences["prefers_high_pay"] = 0.8
            elif avg_positive_rate < avg_negative_rate * 0.9:
                preferences["prefers_high_pay"] = 0.3
            else:
                preferences["prefers_high_pay"] = 0.5

        return preferences
