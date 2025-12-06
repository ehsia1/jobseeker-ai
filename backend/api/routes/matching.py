"""Job matching and recommendation routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User
from backend.models.subscription import Subscription
from backend.api.dependencies import get_current_user, require_job_search
from backend.services.matching_service import MatchingService

try:
    from backend.workers.job_matching import generate_matches_for_user_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    generate_matches_for_user_task = None

router = APIRouter()


@router.post("/generate")
async def generate_matches(
    current_user: User = Depends(get_current_user),
    subscription: Optional[Subscription] = Depends(require_job_search),
    db: AsyncSession = Depends(get_db)
):
    """Generate new job matches for current user.

    Usage limits apply based on subscription tier.
    """
    # Trigger background task
    task_result = generate_matches_for_user_task.delay(str(current_user.id))
    
    return {
        "message": "Match generation started",
        "task_id": task_result.id,
        "user_id": str(current_user.id)
    }


@router.post("/generate-sync")
async def generate_matches_sync(
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(70.0, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    subscription: Optional[Subscription] = Depends(require_job_search),
    db: AsyncSession = Depends(get_db)
):
    """Generate matches synchronously (immediate response).

    Usage limits apply based on subscription tier.
    """
    
    matching_service = MatchingService(db)
    
    try:
        matches = await matching_service.generate_matches_for_user(
            user_id=str(current_user.id),
            limit=limit,
            min_score=min_score
        )
        
        return {
            "matches_generated": len(matches),
            "matches": [
                {
                    "id": str(match.id),
                    "job_id": str(match.job_id),
                    "score": float(match.score),
                    "explanation": match.explanation
                }
                for match in matches[:10]  # Return first 10 for preview
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Match generation failed: {str(e)}"
        )


@router.get("/similar/{job_id}")
async def get_similar_jobs(
    job_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find jobs similar to a given job."""
    
    matching_service = MatchingService(db)
    
    try:
        similar_jobs = await matching_service.get_similar_jobs(job_id, limit)
        
        return {
            "source_job_id": job_id,
            "similar_jobs": [
                {
                    "id": str(job.id),
                    "title": job.title,
                    "company": job.company,
                    "skills": job.skills,
                    "remote": job.remote
                }
                for job in similar_jobs
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Similar job search failed: {str(e)}"
        )


@router.post("/recalculate/{match_id}")
async def recalculate_match_score(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Recalculate score for an existing match."""
    
    if CELERY_AVAILABLE:
        from backend.workers.job_matching import recalculate_match_score_task
        # Trigger background task
        task_result = recalculate_match_score_task.delay(match_id)
        
        return {
            "message": "Score recalculation started",
            "task_id": task_result.id,
            "match_id": match_id
        }
    else:
        return {
            "message": "Celery not available - recalculation would run synchronously",
            "match_id": match_id
    }