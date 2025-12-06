"""User feedback routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from backend.database import get_db
from backend.models.user import User
from backend.models.feedback import UserFeedback
from backend.api.schemas.feedback import UserFeedbackCreate, UserFeedbackRead
from backend.api.routes.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=UserFeedbackRead)
async def create_feedback(
    feedback_data: UserFeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create user feedback for a job match."""
    
    feedback = UserFeedback(
        user_id=current_user.id,
        job_id=feedback_data.job_id,
        match_id=feedback_data.match_id,
        action=feedback_data.action,
        feedback_text=feedback_data.feedback_text,
        metadata=feedback_data.metadata or {}
    )
    
    # Set feedback type based on action
    if feedback_data.action in {"saved", "applied", "interviewed", "hired"}:
        feedback.feedback_type = "positive"
    elif feedback_data.action in {"rejected"}:
        feedback.feedback_type = "negative"
    else:
        feedback.feedback_type = "neutral"
    
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    return feedback


@router.get("/", response_model=List[UserFeedbackRead])
async def get_user_feedback(
    action: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's feedback history."""
    
    query = select(UserFeedback).where(
        UserFeedback.user_id == current_user.id
    ).order_by(desc(UserFeedback.created_at))
    
    if action:
        query = query.where(UserFeedback.action == action)
    
    result = await db.execute(query)
    feedback_list = result.scalars().all()
    
    return feedback_list


@router.get("/{feedback_id}", response_model=UserFeedbackRead)
async def get_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific feedback by ID."""
    
    result = await db.execute(
        select(UserFeedback)
        .where(
            and_(
                UserFeedback.id == feedback_id,
                UserFeedback.user_id == current_user.id
            )
        )
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    return feedback