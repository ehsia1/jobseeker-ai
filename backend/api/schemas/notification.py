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
    metadata: Dict
    sent_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    
    # Computed properties
    is_delivered: bool
    is_failed: bool
    can_retry: bool
    recipient_info: Dict
    template_data: Dict