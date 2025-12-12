"""Notification model for user alerts and communications."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Notification(Base):
    """User notifications for job matches and system updates."""
    
    __tablename__ = "notifications"
    __table_args__ = {"schema": "jobseeker"}
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobseeker.users.id", ondelete="CASCADE"), nullable=False)
    
    # Notification details
    type = Column(String(50), nullable=False, index=True)
    # Types: "email", "slack", "webhook", "push", "sms"
    
    status = Column(String(50), default="pending", nullable=False, index=True)
    # Status: "pending", "sent", "failed", "retrying"
    
    subject = Column(Text)  # Email subject or notification title
    content = Column(Text)  # HTML/markdown content or message

    # User read status (for in-app notifications)
    read = Column(Boolean, default=False, nullable=False)
    
    # Delivery metadata
    notification_metadata = Column(JSONB, nullable=False, default=dict)
    # Contains: recipient info, template data, delivery settings
    
    # Timing
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)  # Error details if delivery failed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    @property
    def is_delivered(self) -> bool:
        """Check if notification was successfully delivered."""
        return self.status == "sent"
    
    @property
    def is_failed(self) -> bool:
        """Check if notification delivery failed."""
        return self.status == "failed"
    
    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.status in {"failed", "retrying"}
    
    @property
    def recipient_info(self) -> Dict:
        """Get recipient information from metadata."""
        return self.notification_metadata.get("recipient", {})
    
    @property
    def template_data(self) -> Dict:
        """Get template data from metadata."""
        return self.notification_metadata.get("template_data", {})
    
    def mark_sent(self) -> None:
        """Mark notification as sent."""
        self.status = "sent"
        self.sent_at = datetime.utcnow()
        self.error_message = None
    
    def mark_failed(self, error_message: str) -> None:
        """Mark notification as failed with error message."""
        self.status = "failed"
        self.error_message = error_message
    
    @classmethod
    def create_email_digest(
        cls,
        user_id: UUID,
        subject: str,
        content: str,
        recipient_email: str,
        job_matches: Optional[list] = None
    ) -> "Notification":
        """Create email digest notification."""
        
        metadata = {
            "recipient": {"email": recipient_email},
            "template_data": {
                "job_matches": job_matches or [],
                "digest_type": "daily"
            }
        }
        
        return cls(
            user_id=user_id,
            type="email",
            subject=subject,
            content=content,
            notification_metadata=metadata
        )
    
    @classmethod
    def create_slack_notification(
        cls,
        user_id: UUID,
        content: str,
        slack_channel: str,
        job_matches: Optional[list] = None
    ) -> "Notification":
        """Create Slack notification."""
        
        metadata = {
            "recipient": {"slack_channel": slack_channel},
            "template_data": {
                "job_matches": job_matches or []
            }
        }
        
        return cls(
            user_id=user_id,
            type="slack",
            subject="New Job Matches",
            content=content,
            notification_metadata=metadata
        )