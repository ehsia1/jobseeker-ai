"""Notification Pydantic schemas."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class NotificationBase(BaseModel):
    """Base notification schema."""
    type: str = Field(..., pattern="^(email|slack|webhook|push|sms)$")
    subject: Optional[str] = None
    content: str


class NotificationCreate(NotificationBase):
    """Notification creation schema."""
    metadata: Dict = Field(default_factory=dict)


class NotificationRead(NotificationBase):
    """Notification read schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: str
    read: bool = False
    notification_metadata: Dict = Field(default_factory=dict, alias="metadata")
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    # Computed properties
    is_delivered: bool = False
    is_failed: bool = False
    can_retry: bool = False
    recipient_info: Dict = Field(default_factory=dict)
    template_data: Dict = Field(default_factory=dict)