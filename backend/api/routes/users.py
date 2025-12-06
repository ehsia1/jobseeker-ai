"""User management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.api.schemas.user import UserRead, UserProfileRead, UserProfileUpdate, UserWithProfile
from backend.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/profile", response_model=UserProfileRead)
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


@router.put("/profile", response_model=UserProfileRead)
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


@router.delete("/profile")
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


@router.get("/me", response_model=UserWithProfile)
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