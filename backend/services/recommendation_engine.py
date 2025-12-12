"""ML-powered recommendation engine for personalized job matching."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from backend.models.job import Job, JobMatch
from backend.models.user import UserProfile
from backend.models.recommendation import (
    UserPreferenceModel,
    RecommendationLog,
    SimilarUserCluster,
    UserClusterMembership,
)
from backend.services.feedback_service import FeedbackCollectionService
from backend.services.scoring_service import ScoringService, ScoreBreakdown

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """ML-powered recommendation engine that learns from user feedback."""

    # Minimum interactions before personalizing
    MIN_INTERACTIONS_FOR_PERSONALIZATION = 5

    # Confidence thresholds
    LOW_CONFIDENCE = 0.3
    MEDIUM_CONFIDENCE = 0.6
    HIGH_CONFIDENCE = 0.8

    # Weight adjustment bounds
    MIN_WEIGHT_MULTIPLIER = 0.5
    MAX_WEIGHT_MULTIPLIER = 2.0

    # Learning rate for weight updates
    LEARNING_RATE = 0.1

    def __init__(self, db: AsyncSession):
        self.db = db
        self.feedback_service = FeedbackCollectionService(db)

    async def get_personalized_recommendations(
        self,
        user_id: UUID,
        jobs: List[Job],
        profile: UserProfile,
        base_scorer: ScoringService,
        limit: int = 20,
    ) -> List[Tuple[Job, float, Dict[str, Any]]]:
        """
        Get personalized job recommendations with ML adjustments.

        Args:
            user_id: User ID
            jobs: List of candidate jobs
            profile: User's profile
            base_scorer: Base scoring service
            limit: Maximum recommendations

        Returns:
            List of (job, final_score, recommendation_details) tuples
        """
        # Get or create user preference model
        preference_model = await self._get_or_create_preference_model(user_id)

        recommendations = []

        for job in jobs:
            try:
                # Get base score
                base_breakdown = base_scorer.score_job(job, profile)
                base_score = base_breakdown.total_score

                # Apply ML adjustments
                ml_adjustment, adjustment_details = await self._calculate_ml_adjustment(
                    user_id, job, preference_model
                )

                # Calculate final score
                final_score = min(100.0, max(0.0, base_score + ml_adjustment))

                # Log recommendation
                await self._log_recommendation(
                    user_id=user_id,
                    job_id=job.id,
                    base_score=base_score,
                    ml_adjustment=ml_adjustment,
                    final_score=final_score,
                    algorithm_version=preference_model.model_version,
                    score_breakdown=adjustment_details,
                )

                recommendations.append((
                    job,
                    final_score,
                    {
                        "base_score": base_score,
                        "ml_adjustment": ml_adjustment,
                        "final_score": final_score,
                        "confidence": preference_model.confidence_score,
                        "factors": adjustment_details,
                        "base_breakdown": base_breakdown.to_dict(),
                    }
                ))

            except Exception as e:
                logger.error(f"Error scoring job {job.id}: {e}")
                # Fall back to base score
                base_breakdown = base_scorer.score_job(job, profile)
                recommendations.append((
                    job,
                    base_breakdown.total_score,
                    {"base_score": base_breakdown.total_score, "ml_adjustment": 0.0}
                ))

        # Sort by final score
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:limit]

    async def _calculate_ml_adjustment(
        self,
        user_id: UUID,
        job: Job,
        preference_model: UserPreferenceModel,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate ML score adjustment based on learned preferences.

        Returns:
            Tuple of (adjustment_value, details_dict)
        """
        adjustment = 0.0
        details = {
            "skill_boost": 0.0,
            "company_boost": 0.0,
            "preference_boost": 0.0,
            "confidence": preference_model.confidence_score,
        }

        # Check if we have enough data
        if preference_model.total_interactions < self.MIN_INTERACTIONS_FOR_PERSONALIZATION:
            details["insufficient_data"] = True
            return adjustment, details

        # Scale adjustments by confidence
        confidence_multiplier = preference_model.confidence_score

        # 1. Skill preference adjustment
        skill_preferences = preference_model.skill_preferences or {}
        job_skills = [s.lower() for s in (job.skills or [])]

        skill_boost = 0.0
        matched_skills = []
        for skill in job_skills:
            if skill in skill_preferences:
                pref_score = skill_preferences[skill]
                skill_boost += pref_score * 5.0  # Scale to meaningful points
                matched_skills.append((skill, pref_score))

        if job_skills:
            skill_boost = skill_boost / len(job_skills)  # Normalize

        details["skill_boost"] = skill_boost * confidence_multiplier
        details["matched_skill_preferences"] = matched_skills
        adjustment += skill_boost * confidence_multiplier

        # 2. Company preference adjustment
        company_preferences = preference_model.company_preferences or {}
        company = (job.company or "").lower()

        if company and company in company_preferences:
            company_boost = company_preferences[company] * 10.0  # Significant boost
            details["company_boost"] = company_boost * confidence_multiplier
            adjustment += company_boost * confidence_multiplier

        # 3. Implicit preference adjustments
        learned_prefs = preference_model.learned_preferences or {}

        # Remote preference
        if "prefers_remote" in learned_prefs and job.remote:
            remote_pref = learned_prefs["prefers_remote"]
            remote_boost = (remote_pref - 0.5) * 10.0  # -5 to +5 points
            details["remote_boost"] = remote_boost * confidence_multiplier
            adjustment += remote_boost * confidence_multiplier

        # High pay preference
        if "prefers_high_pay" in learned_prefs and job.rate_max:
            pay_pref = learned_prefs["prefers_high_pay"]
            # Higher pay preference = boost for high-paying jobs
            if pay_pref > 0.6:
                pay_boost = (pay_pref - 0.5) * 5.0
                details["pay_preference_boost"] = pay_boost * confidence_multiplier
                adjustment += pay_boost * confidence_multiplier

        details["preference_boost"] = details.get("remote_boost", 0) + details.get("pay_preference_boost", 0)

        # Clamp total adjustment
        max_adjustment = 15.0  # Maximum ML adjustment
        adjustment = max(-max_adjustment, min(max_adjustment, adjustment))

        return adjustment, details

    async def update_user_preferences(
        self,
        user_id: UUID,
        force_update: bool = False,
    ) -> UserPreferenceModel:
        """
        Update user preference model based on accumulated feedback.

        Args:
            user_id: User ID
            force_update: Force update even if not enough new data

        Returns:
            Updated UserPreferenceModel
        """
        preference_model = await self._get_or_create_preference_model(user_id)

        # Get feedback statistics
        stats = await self.feedback_service.get_feedback_statistics(user_id)

        # Check if update is needed
        new_interactions = stats["total_interactions"] - preference_model.total_interactions

        if not force_update and new_interactions < 5:
            logger.info(f"Not enough new interactions for user {user_id}: {new_interactions}")
            return preference_model

        logger.info(f"Updating preferences for user {user_id} with {new_interactions} new interactions")

        # Get training samples
        samples = await self.feedback_service.get_training_samples(user_id)

        # Analyze preferences
        skill_prefs = await self.feedback_service.analyze_skill_preferences(user_id)
        company_prefs = await self.feedback_service.analyze_company_preferences(user_id)
        implicit_prefs = await self.feedback_service.get_implicit_preferences(user_id)

        # Calculate weight adjustments based on feedback patterns
        weight_adjustments = await self._calculate_weight_adjustments(user_id, stats)

        # Calculate confidence score
        confidence = self._calculate_confidence(
            positive_samples=len(samples["positive_samples"]),
            negative_samples=len(samples["negative_samples"]),
            total_interactions=stats["total_interactions"],
        )

        # Update model
        preference_model.skill_preferences = skill_prefs
        preference_model.company_preferences = company_prefs
        preference_model.learned_preferences = implicit_prefs
        preference_model.weight_adjustments = weight_adjustments
        preference_model.confidence_score = confidence
        preference_model.positive_samples = len(samples["positive_samples"])
        preference_model.negative_samples = len(samples["negative_samples"])
        preference_model.total_interactions = stats["total_interactions"]
        preference_model.last_trained_at = datetime.utcnow()

        # Increment model version
        current_version = preference_model.model_version or "1.0.0"
        try:
            parts = current_version.split(".")
            if len(parts) == 3:
                patch = int(parts[2]) + 1
                preference_model.model_version = f"{parts[0]}.{parts[1]}.{patch}"
            else:
                preference_model.model_version = "1.0.1"
        except (ValueError, IndexError):
            preference_model.model_version = "1.0.1"

        await self.db.commit()
        await self.db.refresh(preference_model)

        logger.info(f"Updated preference model for user {user_id}, confidence: {confidence:.2f}")

        return preference_model

    async def _calculate_weight_adjustments(
        self,
        user_id: UUID,
        stats: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Calculate scoring weight adjustments based on user behavior.

        Returns:
            Dictionary of weight multipliers for each scoring factor
        """
        adjustments = {
            "skill_match": 1.0,
            "experience_match": 1.0,
            "compensation_match": 1.0,
            "location_match": 1.0,
            "semantic_similarity": 1.0,
        }

        # Get recent applied jobs for pattern analysis
        history = await self.feedback_service.get_user_feedback_history(user_id, days_back=60)

        if not history:
            return adjustments

        # Analyze what factors correlate with positive actions
        applied_count = sum(1 for f in history if f.action == "applied")
        saved_count = sum(1 for f in history if f.action == "saved")
        rejected_count = sum(1 for f in history if f.action == "rejected")

        total_positive = applied_count + saved_count
        total_actions = total_positive + rejected_count

        if total_actions < 10:
            return adjustments

        # If user applies a lot, they value skill matching highly
        apply_rate = applied_count / max(1, total_actions)
        if apply_rate > 0.3:
            adjustments["skill_match"] = 1.2

        # If engagement ratio is high, boost semantic matching
        engagement_ratio = stats.get("engagement_ratio", 0.5)
        if engagement_ratio > 0.7:
            adjustments["semantic_similarity"] = 1.15

        return adjustments

    def _calculate_confidence(
        self,
        positive_samples: int,
        negative_samples: int,
        total_interactions: int,
    ) -> float:
        """
        Calculate confidence score for the preference model.

        Returns:
            Confidence score between 0 and 1
        """
        if total_interactions == 0:
            return 0.0

        # Factors that increase confidence:
        # 1. More total interactions
        interaction_confidence = min(1.0, total_interactions / 50)

        # 2. Balance of positive and negative feedback
        if positive_samples + negative_samples == 0:
            balance_confidence = 0.0
        else:
            ratio = min(positive_samples, negative_samples) / max(positive_samples, negative_samples, 1)
            balance_confidence = ratio * 0.5 + 0.5  # 0.5 to 1.0

        # 3. Minimum samples
        sample_confidence = min(1.0, (positive_samples + negative_samples) / 20)

        # Weighted average
        confidence = (
            interaction_confidence * 0.4 +
            balance_confidence * 0.3 +
            sample_confidence * 0.3
        )

        return min(1.0, confidence)

    async def _get_or_create_preference_model(
        self,
        user_id: UUID,
    ) -> UserPreferenceModel:
        """Get existing preference model or create new one."""
        result = await self.db.execute(
            select(UserPreferenceModel).where(UserPreferenceModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            model = UserPreferenceModel(
                user_id=user_id,
                weight_adjustments={},
                skill_preferences={},
                company_preferences={},
                learned_preferences={},
                confidence_score=0.0,
                model_version="1.0.0",
            )
            self.db.add(model)
            await self.db.commit()
            await self.db.refresh(model)

        return model

    async def _log_recommendation(
        self,
        user_id: UUID,
        job_id: UUID,
        base_score: float,
        ml_adjustment: float,
        final_score: float,
        algorithm_version: str,
        score_breakdown: Dict[str, Any],
    ) -> RecommendationLog:
        """Log a recommendation for analytics."""
        log = RecommendationLog(
            user_id=user_id,
            job_id=job_id,
            base_score=base_score,
            ml_adjustment=ml_adjustment,
            final_score=final_score,
            algorithm_version=algorithm_version,
            score_breakdown=score_breakdown,
        )
        self.db.add(log)
        # Don't commit here - let the caller handle transaction
        return log

    async def get_recommendation_analytics(
        self,
        user_id: UUID,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Get analytics on recommendation performance.

        Args:
            user_id: User ID
            days_back: Number of days to analyze

        Returns:
            Analytics dictionary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get recommendation logs
        result = await self.db.execute(
            select(RecommendationLog)
            .where(
                and_(
                    RecommendationLog.user_id == user_id,
                    RecommendationLog.created_at >= cutoff_date,
                )
            )
        )
        logs = result.scalars().all()

        if not logs:
            return {
                "total_recommendations": 0,
                "view_rate": 0.0,
                "click_rate": 0.0,
                "save_rate": 0.0,
                "apply_rate": 0.0,
                "avg_base_score": 0.0,
                "avg_ml_adjustment": 0.0,
                "avg_final_score": 0.0,
            }

        total = len(logs)
        viewed = sum(1 for l in logs if l.was_viewed)
        clicked = sum(1 for l in logs if l.was_clicked)
        saved = sum(1 for l in logs if l.was_saved)
        applied = sum(1 for l in logs if l.was_applied)

        return {
            "total_recommendations": total,
            "view_rate": viewed / total,
            "click_rate": clicked / total,
            "save_rate": saved / total,
            "apply_rate": applied / total,
            "avg_base_score": sum(l.base_score for l in logs) / total,
            "avg_ml_adjustment": sum(l.ml_adjustment for l in logs) / total,
            "avg_final_score": sum(l.final_score for l in logs) / total,
            "days_analyzed": days_back,
        }

    async def find_similar_users(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> List[Tuple[UUID, float]]:
        """
        Find users with similar preferences for collaborative filtering.

        Args:
            user_id: Source user ID
            limit: Maximum similar users to return

        Returns:
            List of (user_id, similarity_score) tuples
        """
        # Get source user's preference model
        source_model = await self._get_or_create_preference_model(user_id)

        if not source_model.skill_preferences:
            return []

        # Get all other preference models
        result = await self.db.execute(
            select(UserPreferenceModel)
            .where(
                and_(
                    UserPreferenceModel.user_id != user_id,
                    UserPreferenceModel.total_interactions >= self.MIN_INTERACTIONS_FOR_PERSONALIZATION,
                )
            )
        )
        other_models = result.scalars().all()

        similarities = []

        for other in other_models:
            similarity = self._calculate_preference_similarity(source_model, other)
            if similarity > 0.3:  # Minimum similarity threshold
                similarities.append((other.user_id, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:limit]

    def _calculate_preference_similarity(
        self,
        model_a: UserPreferenceModel,
        model_b: UserPreferenceModel,
    ) -> float:
        """Calculate similarity between two preference models."""
        # Compare skill preferences
        skills_a = set(model_a.skill_preferences.keys()) if model_a.skill_preferences else set()
        skills_b = set(model_b.skill_preferences.keys()) if model_b.skill_preferences else set()

        if not skills_a or not skills_b:
            return 0.0

        common_skills = skills_a & skills_b
        all_skills = skills_a | skills_b

        # Jaccard similarity for skills
        skill_jaccard = len(common_skills) / len(all_skills) if all_skills else 0.0

        # Cosine similarity for preference values of common skills
        if common_skills:
            values_a = [model_a.skill_preferences.get(s, 0) for s in common_skills]
            values_b = [model_b.skill_preferences.get(s, 0) for s in common_skills]

            dot_product = sum(a * b for a, b in zip(values_a, values_b))
            norm_a = np.sqrt(sum(v ** 2 for v in values_a))
            norm_b = np.sqrt(sum(v ** 2 for v in values_b))

            if norm_a > 0 and norm_b > 0:
                cosine_sim = dot_product / (norm_a * norm_b)
            else:
                cosine_sim = 0.0
        else:
            cosine_sim = 0.0

        # Compare implicit preferences
        prefs_a = model_a.learned_preferences or {}
        prefs_b = model_b.learned_preferences or {}

        pref_similarity = 0.0
        common_prefs = set(prefs_a.keys()) & set(prefs_b.keys())

        if common_prefs:
            pref_diffs = [abs(prefs_a[p] - prefs_b[p]) for p in common_prefs]
            pref_similarity = 1.0 - (sum(pref_diffs) / len(pref_diffs))

        # Weighted combination
        return (skill_jaccard * 0.3 + cosine_sim * 0.5 + pref_similarity * 0.2)

    async def get_collaborative_recommendations(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on similar users' preferences.

        Args:
            user_id: User ID
            limit: Maximum recommendations

        Returns:
            List of job recommendations from similar users
        """
        similar_users = await self.find_similar_users(user_id, limit=5)

        if not similar_users:
            return []

        # Get jobs that similar users liked but this user hasn't seen
        user_job_ids_result = await self.db.execute(
            select(JobMatch.job_id).where(JobMatch.user_id == user_id)
        )
        user_job_ids = {row[0] for row in user_job_ids_result.all()}

        recommendations = []

        for similar_user_id, similarity in similar_users:
            # Get jobs the similar user applied to or saved
            from backend.models.feedback import UserFeedback

            result = await self.db.execute(
                select(UserFeedback, Job)
                .join(Job, UserFeedback.job_id == Job.id)
                .where(
                    and_(
                        UserFeedback.user_id == similar_user_id,
                        UserFeedback.action.in_(["applied", "saved", "interviewed", "hired"]),
                        ~UserFeedback.job_id.in_(user_job_ids) if user_job_ids else True,
                    )
                )
                .order_by(desc(UserFeedback.created_at))
                .limit(5)
            )

            for feedback, job in result.all():
                recommendations.append({
                    "job_id": str(job.id),
                    "job_title": job.title,
                    "company": job.company,
                    "source_user_similarity": similarity,
                    "source_action": feedback.action,
                    "reason": "Similar users liked this job",
                })

        # Deduplicate and sort by similarity
        seen_jobs = set()
        unique_recommendations = []

        for rec in recommendations:
            if rec["job_id"] not in seen_jobs:
                seen_jobs.add(rec["job_id"])
                unique_recommendations.append(rec)

        unique_recommendations.sort(key=lambda x: x["source_user_similarity"], reverse=True)

        return unique_recommendations[:limit]
