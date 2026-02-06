"""Email service for sending transactional emails."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List

from backend.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        """Initialize email service with SMTP settings."""
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.from_email = settings.email_address or settings.smtp_username

    @property
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.username and self.password)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text fallback (auto-generated if not provided)

        Returns:
            True if email was sent successfully
        """
        if not self.is_configured:
            logger.warning("SMTP not configured, skipping email send")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Plain text fallback
            if not text_content:
                text_content = self._html_to_text(html_content)

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            return False

    def send_bulk_emails(
        self,
        recipients: List[dict],
        subject: str,
        html_template: str,
    ) -> dict:
        """Send emails to multiple recipients.

        Args:
            recipients: List of dicts with 'email' and template variables
            subject: Email subject
            html_template: HTML template with {variable} placeholders

        Returns:
            Dict with 'sent' and 'failed' counts
        """
        results = {"sent": 0, "failed": 0}

        for recipient in recipients:
            email = recipient.get("email")
            if not email:
                results["failed"] += 1
                continue

            # Format template with recipient data
            try:
                html_content = html_template.format(**recipient)
            except KeyError as e:
                logger.error(f"Missing template variable {e} for {email}")
                results["failed"] += 1
                continue

            if self.send_email(email, subject, html_content):
                results["sent"] += 1
            else:
                results["failed"] += 1

        return results

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple version)."""
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
