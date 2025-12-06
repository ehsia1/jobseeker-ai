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


@router.get("/{match_id}", response_model=JobMatchRead)
async def get_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific job match by ID."""
    
    result = await db.execute(
        select(JobMatch)
        .where(
            and_(
                JobMatch.id == match_id,
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


@router.put("/{match_id}/status")
async def update_match_status(
    match_id: str,
    new_status: str = Query(..., pattern="^(viewed|saved|applied|rejected)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update match status (viewed, saved, applied, etc.)."""
    
    result = await db.execute(
        select(JobMatch)
        .where(
            and_(
                JobMatch.id == match_id,
                JobMatch.user_id == current_user.id
            )
        )
    )
    match = result.scalar_one_or_none()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Update status and track application date
    match.status = new_status
    if new_status == "applied":
        from datetime import datetime
        match.applied_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"Match status updated to {new_status}"}


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