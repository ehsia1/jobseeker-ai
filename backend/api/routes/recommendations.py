"""Recommendation engine API routes."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from backend.database import get_db
from backend.api.dependencies import get_current_user
from backend.models.user import User, UserProfile
from backend.models.job import Job, JobMatch
from backend.services.recommendation_engine import RecommendationEngine
from backend.services.feedback_service import FeedbackCollectionService
from backend.services.scoring_service import ScoringService
from backend.services.embedding_service import EmbeddingService
from backend.api.schemas.recommendation import (
    JobRecommendationResponse,
    RecommendationListResponse,
    UserPreferencesResponse,
    RecommendationAnalyticsResponse,
    CollaborativeRecommendationsResponse,
    CollaborativeRecommendationResponse,
    FeedbackStatisticsResponse,
    RecordFeedbackRequest,
    UpdatePreferencesRequest,
    RecommendationHealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/health", response_model=RecommendationHealthResponse)
async def health_check():
    """Check recommendation service health."""
    return RecommendationHealthResponse(
        status="healthy",
        ml_enabled=True,
        supported_actions=[
            "viewed", "clicked", "saved", "applied",
            "rejected", "interviewed", "hired"
        ],
        min_interactions_for_personalization=5,
    )


@router.get("", response_model=RecommendationListResponse)
async def get_recommendations(
    limit: int = Query(default=20, ge=1, le=100, description="Max recommendations"),
    min_score: float = Query(default=50.0, ge=0, le=100, description="Minimum score"),
    include_breakdown: bool = Query(default=False, description="Include score breakdown"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get personalized job recommendations for the current user.

    Returns jobs scored with ML adjustments based on learned preferences.
    """
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found. Please complete your profile first."
        )

    # Get candidate jobs (recent, not yet matched)
    existing_matches_result = await db.execute(
        select(JobMatch.job_id).where(JobMatch.user_id == current_user.id)
    )
    existing_job_ids = [row[0] for row in existing_matches_result.all()]

    jobs_query = select(Job).where(
        ~Job.id.in_(existing_job_ids) if existing_job_ids else True
    ).order_by(desc(Job.posted_at)).limit(100)

    jobs_result = await db.execute(jobs_query)
    jobs = jobs_result.scalars().all()

    if not jobs:
        return RecommendationListResponse(
            recommendations=[],
            total=0,
            model_confidence=0.0,
            personalization_enabled=False,
        )

    # Initialize services
    engine = RecommendationEngine(db)
    embedding_service = EmbeddingService()
    base_scorer = ScoringService(embedding_service)

    # Get personalized recommendations
    recommendations = await engine.get_personalized_recommendations(
        user_id=current_user.id,
        jobs=jobs,
        profile=profile,
        base_scorer=base_scorer,
        limit=limit,
    )

    # Get preference model for confidence
    preference_model = await engine._get_or_create_preference_model(current_user.id)

    # Filter by min score
    filtered_recommendations = [
        (job, score, details)
        for job, score, details in recommendations
        if score >= min_score
    ]

    # Build response
    response_items = []
    for job, final_score, details in filtered_recommendations:
        item = JobRecommendationResponse(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            location=job.location,
            remote=job.remote or False,
            rate_min=float(job.rate_min) if job.rate_min else None,
            rate_max=float(job.rate_max) if job.rate_max else None,
            rate_type=job.rate_type,
            skills=job.skills or [],
            final_score=final_score,
            base_score=details.get("base_score", final_score),
            ml_adjustment=details.get("ml_adjustment", 0.0),
            confidence=details.get("confidence", 0.0),
            score_breakdown=details.get("base_breakdown") if include_breakdown else None,
            ml_factors=details.get("factors") if include_breakdown else None,
        )
        response_items.append(item)

    await db.commit()  # Commit recommendation logs

    return RecommendationListResponse(
        recommendations=response_items,
        total=len(response_items),
        model_confidence=preference_model.confidence_score,
        personalization_enabled=preference_model.total_interactions >= 5,
    )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's learned preferences."""
    engine = RecommendationEngine(db)
    preference_model = await engine._get_or_create_preference_model(current_user.id)

    return UserPreferencesResponse(
        user_id=preference_model.user_id,
        confidence_score=preference_model.confidence_score,
        total_interactions=preference_model.total_interactions,
        positive_samples=preference_model.positive_samples,
        negative_samples=preference_model.negative_samples,
        skill_preferences=preference_model.skill_preferences or {},
        company_preferences=preference_model.company_preferences or {},
        learned_preferences=preference_model.learned_preferences or {},
        weight_adjustments=preference_model.weight_adjustments or {},
        last_trained_at=preference_model.last_trained_at,
        model_version=preference_model.model_version or "1.0.0",
    )


@router.post("/preferences/update", response_model=UserPreferencesResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Force update user preference model based on feedback.

    This triggers retraining of the ML model for this user.
    """
    engine = RecommendationEngine(db)

    try:
        preference_model = await engine.update_user_preferences(
            user_id=current_user.id,
            force_update=request.force_update,
        )

        return UserPreferencesResponse(
            user_id=preference_model.user_id,
            confidence_score=preference_model.confidence_score,
            total_interactions=preference_model.total_interactions,
            positive_samples=preference_model.positive_samples,
            negative_samples=preference_model.negative_samples,
            skill_preferences=preference_model.skill_preferences or {},
            company_preferences=preference_model.company_preferences or {},
            learned_preferences=preference_model.learned_preferences or {},
            weight_adjustments=preference_model.weight_adjustments or {},
            last_trained_at=preference_model.last_trained_at,
            model_version=preference_model.model_version or "1.0.0",
        )

    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/analytics", response_model=RecommendationAnalyticsResponse)
async def get_recommendation_analytics(
    days_back: int = Query(default=30, ge=1, le=90, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics on recommendation performance for the current user."""
    engine = RecommendationEngine(db)

    analytics = await engine.get_recommendation_analytics(
        user_id=current_user.id,
        days_back=days_back,
    )

    return RecommendationAnalyticsResponse(**analytics)


@router.get("/collaborative", response_model=CollaborativeRecommendationsResponse)
async def get_collaborative_recommendations(
    limit: int = Query(default=10, ge=1, le=50, description="Max recommendations"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get job recommendations based on similar users' preferences.

    Uses collaborative filtering to find jobs that similar users liked.
    """
    engine = RecommendationEngine(db)

    # Find similar users
    similar_users = await engine.find_similar_users(
        user_id=current_user.id,
        limit=5,
    )

    # Get collaborative recommendations
    recommendations = await engine.get_collaborative_recommendations(
        user_id=current_user.id,
        limit=limit,
    )

    return CollaborativeRecommendationsResponse(
        recommendations=[
            CollaborativeRecommendationResponse(**rec)
            for rec in recommendations
        ],
        similar_users_found=len(similar_users),
    )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def record_feedback(
    request: RecordFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record user feedback for a job recommendation.

    Valid actions: viewed, clicked, saved, applied, rejected, interviewed, hired
    """
    feedback_service = FeedbackCollectionService(db)

    try:
        feedback = await feedback_service.record_feedback(
            user_id=current_user.id,
            job_id=request.job_id,
            match_id=request.match_id,
            action=request.action,
            feedback_text=request.feedback_text,
            metadata=request.metadata,
        )

        return {
            "id": str(feedback.id),
            "action": feedback.action,
            "feedback_type": feedback.feedback_type,
            "created_at": feedback.created_at.isoformat(),
            "message": f"Feedback recorded: {request.action}",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback"
        )


@router.get("/feedback/stats", response_model=FeedbackStatisticsResponse)
async def get_feedback_statistics(
    days_back: int = Query(default=30, ge=1, le=90, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feedback statistics for the current user."""
    feedback_service = FeedbackCollectionService(db)

    stats = await feedback_service.get_feedback_statistics(
        user_id=current_user.id,
        days_back=days_back,
    )

    return FeedbackStatisticsResponse(**stats)


@router.get("/feedback/history")
async def get_feedback_history(
    days_back: int = Query(default=30, ge=1, le=90, description="Days to look back"),
    limit: int = Query(default=50, ge=1, le=200, description="Max entries"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feedback history for the current user."""
    feedback_service = FeedbackCollectionService(db)

    history = await feedback_service.get_user_feedback_history(
        user_id=current_user.id,
        days_back=days_back,
        limit=limit,
    )

    return {
        "feedback": [
            {
                "id": str(f.id),
                "job_id": str(f.job_id),
                "match_id": str(f.match_id),
                "action": f.action,
                "feedback_type": f.feedback_type,
                "feedback_text": f.feedback_text,
                "created_at": f.created_at.isoformat(),
            }
            for f in history
        ],
        "total": len(history),
        "days_back": days_back,
    }


@router.get("/training-data")
async def get_training_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get training samples derived from user feedback.

    Returns positive and negative samples for ML model training.
    """
    feedback_service = FeedbackCollectionService(db)

    samples = await feedback_service.get_training_samples(
        user_id=current_user.id,
    )

    return samples


@router.get("/skill-analysis")
async def get_skill_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analysis of skill preferences based on feedback.

    Returns preference scores for each skill (-1 to 1).
    """
    feedback_service = FeedbackCollectionService(db)

    skill_prefs = await feedback_service.analyze_skill_preferences(
        user_id=current_user.id,
    )

    # Sort by preference score
    sorted_prefs = sorted(
        skill_prefs.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "skill_preferences": dict(sorted_prefs),
        "top_preferred": [s for s, score in sorted_prefs[:10] if score > 0],
        "least_preferred": [s for s, score in sorted_prefs[-10:] if score < 0],
        "total_skills_analyzed": len(skill_prefs),
    }


@router.get("/company-analysis")
async def get_company_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analysis of company preferences based on feedback.

    Returns preference scores for each company (-1 to 1).
    """
    feedback_service = FeedbackCollectionService(db)

    company_prefs = await feedback_service.analyze_company_preferences(
        user_id=current_user.id,
    )

    # Sort by preference score
    sorted_prefs = sorted(
        company_prefs.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "company_preferences": dict(sorted_prefs),
        "top_preferred": [c for c, score in sorted_prefs[:10] if score > 0],
        "least_preferred": [c for c, score in sorted_prefs[-10:] if score < 0],
        "total_companies_analyzed": len(company_prefs),
    }
