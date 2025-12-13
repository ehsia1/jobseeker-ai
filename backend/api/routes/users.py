"""User management routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.models.notification import Notification
from backend.api.schemas.user import UserRead, UserProfileRead, UserProfileUpdate, UserWithProfile
from backend.api.schemas.notification import NotificationRead
from backend.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/profile/", response_model=UserProfileRead)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile."""
    
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return profile


@router.put("/profile/", response_model=UserProfileRead)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    # Update profile fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    return profile


@router.delete("/profile/")
async def delete_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's profile."""
    
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if profile:
        await db.delete(profile)
        await db.commit()
    
    return {"message": "Profile deleted successfully"}


@router.get("/me/", response_model=UserWithProfile)
async def get_current_user_detailed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user with profile and stats."""
    
    # Get profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    user_dict = UserRead.model_validate(current_user).model_dump()
    if profile:
        user_dict["profile"] = profile

    return user_dict


# Notification routes
@router.get("/me/notifications/")
async def get_user_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's notifications with pagination."""

    # Count total notifications
    count_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # Get paginated notifications
    offset = (page - 1) * size
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    notifications = result.scalars().all()

    return {
        "items": notifications,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 1
    }


@router.put("/me/notifications/{notification_id}/read/")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a single notification as read."""

    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user.id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.read = True
    await db.commit()
    await db.refresh(notification)

    return notification


@router.put("/me/notifications/read-all/")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read."""

    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.read == False)
        .values(read=True)
    )
    await db.commit()

    return {"message": "All notifications marked as read"}