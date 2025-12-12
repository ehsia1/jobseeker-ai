"""Job matching routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.user import User
from backend.models.job import Job, JobMatch
from backend.api.schemas.match import JobMatchRead
from backend.api.routes.auth import get_current_user

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

    # Create new match
    match = JobMatch(
        id=uuid.uuid4(),
        user_id=current_user.id,
        job_id=job_uuid,
        status="new",
        score=70.0,  # Default score, would be calculated by scoring service
        score_breakdown={},
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
    min_score: float = Query(70.0, ge=0, le=100),
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