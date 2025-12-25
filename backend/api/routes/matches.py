"""Job matching routes."""

from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.models.job import Job, JobMatch
from backend.api.schemas.match import JobMatchRead
from backend.api.routes.auth import get_current_user
from backend.services.scoring_service import ScoringService
from backend.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=JobMatchRead)
async def create_match(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new job match for the current user."""
    import uuid
    from uuid import UUID
    from datetime import datetime

    job_id = request.get("job_id")
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_id is required"
        )

    # Convert string to UUID
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if job exists
    job_result = await db.execute(
        select(Job).where(Job.id == job_uuid)
    )
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if match already exists
    existing_result = await db.execute(
        select(JobMatch).where(
            and_(
                JobMatch.job_id == job_uuid,
                JobMatch.user_id == current_user.id
            )
        ).options(selectinload(JobMatch.job))
    )
    existing_match = existing_result.scalar_one_or_none()

    if existing_match:
        return existing_match

    # Get user profile for scoring
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    # Calculate score using scoring service
    score = 50.0  # Default fallback score
    score_breakdown = {}
    explanation = None

    if profile:
        try:
            embedding_service = EmbeddingService()
            scoring_service = ScoringService(embedding_service)
            breakdown = scoring_service.score_job(job, profile)
            score = breakdown.total_score
            score_breakdown = breakdown.to_dict()
            explanation = scoring_service.generate_explanation(job, profile, breakdown)
            logger.info(f"Calculated score {score:.1f} for job {job.title}")
        except Exception as e:
            logger.warning(f"Error calculating score: {e}, using default")
    else:
        logger.warning(f"No profile found for user {current_user.id}, using default score")

    # Create new match with calculated score
    match = JobMatch(
        id=uuid.uuid4(),
        user_id=current_user.id,
        job_id=job_uuid,
        status="new",
        score=score,
        score_breakdown=score_breakdown,
        explanation=explanation,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(match)
    await db.commit()
    await db.refresh(match)

    # Load job relationship
    result = await db.execute(
        select(JobMatch).where(JobMatch.id == match.id).options(selectinload(JobMatch.job))
    )
    match = result.scalar_one()

    return match


@router.get("/", response_model=List[JobMatchRead])
async def get_user_matches(
    status_filter: str = Query(None, pattern="^(new|viewed|saved|applied|rejected)$"),
    min_score: float = Query(40.0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job matches for current user."""
    
    query = select(JobMatch).where(
        JobMatch.user_id == current_user.id
    ).options(
        selectinload(JobMatch.job)
    ).order_by(desc(JobMatch.score))
    
    # Apply filters
    filters = [JobMatch.score >= min_score]
    
    if status_filter:
        filters.append(JobMatch.status == status_filter)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    matches = result.scalars().all()
    
    return matches


@router.get("/{match_id}/", response_model=JobMatchRead)
async def get_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific job match by ID."""
    from uuid import UUID

    try:
        match_uuid = UUID(match_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    result = await db.execute(
        select(JobMatch)
        .where(
            and_(
                JobMatch.id == match_uuid,
                JobMatch.user_id == current_user.id
            )
        )
        .options(selectinload(JobMatch.job))
    )
    match = result.scalar_one_or_none()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    return match


@router.put("/{match_id}/status/")
async def update_match_status(
    match_id: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update match status (viewed, saved, applied, etc.)."""
    from datetime import datetime
    from uuid import UUID

    new_status = request.get("status")
    if not new_status or new_status not in ("new", "viewed", "saved", "applied", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: new, viewed, saved, applied, rejected"
        )

    try:
        match_uuid = UUID(match_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    result = await db.execute(
        select(JobMatch)
        .where(
            and_(
                JobMatch.id == match_uuid,
                JobMatch.user_id == current_user.id
            )
        )
        .options(selectinload(JobMatch.job))
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Update status and track application date
    match.status = new_status
    match.updated_at = datetime.utcnow()
    if new_status == "applied":
        match.applied_at = datetime.utcnow()

    await db.commit()
    await db.refresh(match)

    # Trigger cover letter pre-generation when job is saved
    if new_status == "saved":
        try:
            from backend.workers.agent_tasks import on_job_saved
            on_job_saved(str(current_user.id), str(match.job_id))
            logger.info(f"Triggered cover letter pre-generation for job {match.job_id}")
        except Exception as e:
            # Don't fail the request if background task fails to queue
            logger.warning(f"Failed to trigger cover letter generation: {e}")

    return match


@router.put("/{match_id}/notes/")
async def update_match_notes(
    match_id: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update match notes."""
    from datetime import datetime
    from uuid import UUID

    client_notes = request.get("client_notes")

    try:
        match_uuid = UUID(match_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    result = await db.execute(
        select(JobMatch)
        .where(
            and_(
                JobMatch.id == match_uuid,
                JobMatch.user_id == current_user.id
            )
        )
        .options(selectinload(JobMatch.job))
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    match.client_notes = client_notes
    match.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(match)

    return match


@router.get("/stats/summary")
async def get_match_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user match statistics."""
    
    # TODO: Implement match statistics aggregation
    # This would include counts by status, average score, etc.
    
    return {
        "total_matches": 0,
        "new_matches": 0,
        "saved_matches": 0,
        "applied_matches": 0,
        "average_score": 0.0,
        "message": "Statistics not yet implemented"
    }