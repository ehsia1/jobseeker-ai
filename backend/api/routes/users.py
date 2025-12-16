"""User management routes."""

import os
import logging
from pathlib import Path
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from backend.config import settings
from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.models.notification import Notification
from backend.api.schemas.user import UserRead, UserProfileRead, UserProfileUpdate, UserWithProfile, UserContactUpdate
from backend.api.schemas.notification import NotificationRead
from backend.api.routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Allowed image types for avatars
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


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


@router.put("/me/", response_model=UserRead)
async def update_current_user(
    user_data: UserContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's contact info (full_name, phone)."""

    # Update user fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload or update user's profile picture."""

    # Validate content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES.keys())}"
        )

    # Read file content and check size
    content = await file.read()
    if len(content) > settings.max_avatar_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_avatar_size // (1024*1024)}MB"
        )

    # Create uploads directory if it doesn't exist
    avatars_dir = Path(settings.uploads_dir) / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename using user ID
    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    filename = f"{current_user.id}.{ext}"
    filepath = avatars_dir / filename

    # Delete old avatar if it exists with different extension
    for old_ext in ALLOWED_IMAGE_TYPES.values():
        old_file = avatars_dir / f"{current_user.id}.{old_ext}"
        if old_file.exists() and old_file != filepath:
            old_file.unlink()

    # Save new avatar
    with open(filepath, "wb") as f:
        f.write(content)

    # Update user's profile picture URL
    current_user.profile_picture_url = f"/users/me/avatar/{filename}"
    await db.commit()
    await db.refresh(current_user)

    logger.info(f"Avatar uploaded for user {current_user.id}")
    return current_user


@router.get("/me/avatar/{filename}")
async def get_avatar(filename: str):
    """Serve user avatar image."""

    avatars_dir = Path(settings.uploads_dir) / "avatars"
    filepath = avatars_dir / filename

    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found"
        )

    # Security: ensure filename doesn't escape avatars directory
    if not filepath.resolve().is_relative_to(avatars_dir.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    return FileResponse(filepath)


@router.delete("/me/avatar", response_model=UserRead)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user's profile picture."""

    if not current_user.profile_picture_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No avatar to delete"
        )

    # Delete file from disk
    avatars_dir = Path(settings.uploads_dir) / "avatars"
    for ext in ALLOWED_IMAGE_TYPES.values():
        filepath = avatars_dir / f"{current_user.id}.{ext}"
        if filepath.exists():
            filepath.unlink()

    # Clear URL from database
    current_user.profile_picture_url = None
    await db.commit()
    await db.refresh(current_user)

    logger.info(f"Avatar deleted for user {current_user.id}")
    return current_user


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