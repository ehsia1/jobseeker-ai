"""Pydantic schemas for API serialization."""

from backend.api.schemas.user import UserCreate, UserRead, UserUpdate, UserProfileCreate, UserProfileRead, UserProfileUpdate
from backend.api.schemas.job import JobCreate, JobRead, JobUpdate
from backend.api.schemas.match import JobMatchCreate, JobMatchRead, JobMatchUpdate
from backend.api.schemas.feedback import UserFeedbackCreate, UserFeedbackRead
from backend.api.schemas.notification import NotificationCreate, NotificationRead

__all__ = [
    "UserCreate",
    "UserRead", 
    "UserUpdate",
    "UserProfileCreate",
    "UserProfileRead",
    "UserProfileUpdate",
    "JobCreate",
    "JobRead",
    "JobUpdate",
    "JobMatchCreate",
    "JobMatchRead",
    "JobMatchUpdate", 
    "UserFeedbackCreate",
    "UserFeedbackRead",
    "NotificationCreate",
    "NotificationRead",
]