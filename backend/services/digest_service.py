"""Digest service for generating and sending daily job match digests."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.user import User, UserProfile
from backend.models.job import Job, JobMatch
from backend.models.notification import Notification
from backend.config import settings
from backend.services.email_service import get_email_service, EmailService

logger = logging.getLogger(__name__)


class DigestService:
    """Service for generating and sending daily job match digests."""

    def __init__(
        self,
        db: AsyncSession,
        email_service: Optional[EmailService] = None,
    ):
        """Initialize digest service.

        Args:
            db: Database session
            email_service: Optional email service (uses default if not provided)
        """
        self.db = db
        self.email_service = email_service or get_email_service()

    async def get_users_for_digest(self) -> List[User]:
        """Get all active users who should receive a digest.

        Returns:
            List of User objects with profiles loaded
        """
        query = (
            select(User)
            .options(joinedload(User.profile))
            .where(
                and_(
                    User.is_active == True,
                    # Could add: filter by digest_enabled preference
                )
            )
        )

        result = await self.db.execute(query)
        users = result.unique().scalars().all()

        # Filter to users who have digest enabled (default: True)
        return [
            user for user in users
            if self._is_digest_enabled(user)
        ]

    def _is_digest_enabled(self, user: User) -> bool:
        """Check if user has digest enabled in preferences."""
        if not user.profile:
            return True  # Default: enabled

        preferences = user.profile.preferences or {}
        digest_settings = preferences.get("digest", {})
        return digest_settings.get("enabled", True)

    def _get_digest_frequency(self, user: User) -> str:
        """Get user's preferred digest frequency."""
        if not user.profile:
            return "daily"

        preferences = user.profile.preferences or {}
        digest_settings = preferences.get("digest", {})
        return digest_settings.get("frequency", "daily")

    async def get_new_matches_for_user(
        self,
        user_id: UUID,
        since: Optional[datetime] = None,
        limit: int = None,
    ) -> List[JobMatch]:
        """Get new/unviewed job matches for a user since last digest.

        Args:
            user_id: User ID to get matches for
            since: Optional datetime to filter matches created after
            limit: Maximum matches to return (defaults to settings.max_jobs_per_digest)

        Returns:
            List of JobMatch objects with Job eagerly loaded
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=1)

        if limit is None:
            limit = settings.max_jobs_per_digest

        query = (
            select(JobMatch)
            .options(joinedload(JobMatch.job))
            .where(
                and_(
                    JobMatch.user_id == user_id,
                    JobMatch.created_at >= since,
                    or_(
                        JobMatch.status == "new",
                        JobMatch.status == "viewed",
                    ),
                )
            )
            .order_by(JobMatch.score.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def get_digest_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get statistics for user's digest.

        Args:
            user_id: User ID

        Returns:
            Dict with stats like total_new, high_quality_count, etc.
        """
        since = datetime.utcnow() - timedelta(days=1)

        # Get all new matches
        query = (
            select(JobMatch)
            .where(
                and_(
                    JobMatch.user_id == user_id,
                    JobMatch.created_at >= since,
                )
            )
        )
        result = await self.db.execute(query)
        matches = result.scalars().all()

        high_quality = [m for m in matches if m.score >= 80]
        applied = [m for m in matches if m.status == "applied"]

        return {
            "total_new": len(matches),
            "high_quality_count": len(high_quality),
            "applied_count": len(applied),
            "average_score": sum(float(m.score) for m in matches) / len(matches) if matches else 0,
        }

    def generate_digest_html(
        self,
        user: User,
        matches: List[JobMatch],
        stats: Dict[str, Any],
    ) -> str:
        """Generate HTML content for the digest email.

        Args:
            user: User receiving the digest
            matches: List of job matches to include
            stats: Digest statistics

        Returns:
            HTML string for email body
        """
        if not matches:
            return self._generate_empty_digest_html(user)

        jobs_html = ""
        for match in matches:
            job = match.job
            score_color = self._get_score_color(float(match.score))

            jobs_html += f"""
            <div style="background: white; border-radius: 8px; padding: 20px; margin-bottom: 16px; border: 1px solid #e5e7eb;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3 style="margin: 0 0 8px 0; color: #1f2937; font-size: 18px;">{job.title}</h3>
                        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">{job.company or 'Company not specified'}</p>
                    </div>
                    <div style="background: {score_color}; color: white; padding: 6px 12px; border-radius: 16px; font-weight: 600; font-size: 14px;">
                        {int(match.score)}% match
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <span style="color: #6b7280; font-size: 13px;">
                        {job.location or 'Location not specified'}
                        {' • Remote' if job.remote else ''}
                        {f' • {job.rate_range_text}' if job.rate_min or job.rate_max else ''}
                    </span>
                </div>
                {f'<p style="margin: 12px 0 0 0; color: #4b5563; font-size: 14px; line-height: 1.5;">{match.explanation[:200]}...</p>' if match.explanation else ''}
                <div style="margin-top: 16px;">
                    <a href="{job.url}" style="background: #2563eb; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 500;">View Job</a>
                </div>
            </div>
            """

        username = user.full_name or user.username

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); padding: 32px; border-radius: 12px 12px 0 0; text-align: center;">
                    <h1 style="margin: 0; color: white; font-size: 28px;">Your Daily Job Matches</h1>
                    <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">Hi {username}! Here are your top opportunities</p>
                </div>

                <!-- Stats -->
                <div style="background: white; padding: 20px; border-bottom: 1px solid #e5e7eb;">
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <div style="font-size: 28px; font-weight: 700; color: #2563eb;">{stats['total_new']}</div>
                            <div style="font-size: 12px; color: #6b7280; text-transform: uppercase;">New Matches</div>
                        </div>
                        <div>
                            <div style="font-size: 28px; font-weight: 700; color: #059669;">{stats['high_quality_count']}</div>
                            <div style="font-size: 12px; color: #6b7280; text-transform: uppercase;">High Quality</div>
                        </div>
                        <div>
                            <div style="font-size: 28px; font-weight: 700; color: #7c3aed;">{int(stats['average_score'])}%</div>
                            <div style="font-size: 12px; color: #6b7280; text-transform: uppercase;">Avg Match</div>
                        </div>
                    </div>
                </div>

                <!-- Jobs List -->
                <div style="background: #f9fafb; padding: 20px; border-radius: 0 0 12px 12px;">
                    <h2 style="margin: 0 0 16px 0; color: #1f2937; font-size: 18px;">Top {len(matches)} Opportunities</h2>
                    {jobs_html}

                    <!-- CTA -->
                    <div style="text-align: center; margin-top: 24px;">
                        <a href="#" style="background: #2563eb; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: 600;">View All Matches in App</a>
                    </div>
                </div>

                <!-- Footer -->
                <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
                    <p style="margin: 0;">You're receiving this because you have daily digests enabled.</p>
                    <p style="margin: 8px 0 0 0;">
                        <a href="#" style="color: #6b7280;">Manage preferences</a> •
                        <a href="#" style="color: #6b7280;">Unsubscribe</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _generate_empty_digest_html(self, user: User) -> str:
        """Generate HTML for when there are no new matches."""
        username = user.full_name or user.username

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background: white; padding: 40px; border-radius: 12px; text-align: center;">
                    <h1 style="margin: 0 0 16px 0; color: #1f2937; font-size: 24px;">No New Matches Today</h1>
                    <p style="margin: 0 0 24px 0; color: #6b7280; font-size: 16px;">
                        Hi {username}! We didn't find any new job matches for you today, but we're always looking.
                    </p>
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">
                        Try updating your profile or adding more skills to get better matches.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_score_color(self, score: float) -> str:
        """Get color for score badge."""
        if score >= 85:
            return "#059669"  # Green
        elif score >= 70:
            return "#2563eb"  # Blue
        elif score >= 50:
            return "#d97706"  # Orange
        return "#6b7280"  # Gray

    async def send_digest_to_user(self, user: User) -> bool:
        """Generate and send digest email to a user.

        Args:
            user: User to send digest to

        Returns:
            True if digest was sent successfully
        """
        try:
            # Get new matches
            matches = await self.get_new_matches_for_user(user.id)
            stats = await self.get_digest_stats(user.id)

            # Generate email content
            html_content = self.generate_digest_html(user, matches, stats)

            # Send email
            subject = f"Your Daily Job Matches - {stats['total_new']} new opportunities"
            success = self.email_service.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
            )

            if success:
                # Create notification record
                notification = Notification.create_email_digest(
                    user_id=user.id,
                    subject=subject,
                    content=html_content,
                    recipient_email=user.email,
                    job_matches=[str(m.id) for m in matches],
                )
                notification.mark_sent()
                self.db.add(notification)
                await self.db.commit()

                logger.info(f"Digest sent successfully to {user.email}")
            else:
                # Record failed notification
                notification = Notification.create_email_digest(
                    user_id=user.id,
                    subject=subject,
                    content=html_content,
                    recipient_email=user.email,
                )
                notification.mark_failed("Email delivery failed")
                self.db.add(notification)
                await self.db.commit()

                logger.warning(f"Failed to send digest to {user.email}")

            return success

        except Exception as e:
            logger.error(f"Error sending digest to {user.email}: {e}")
            return False

    async def send_all_digests(self) -> Dict[str, int]:
        """Send digests to all eligible users.

        Returns:
            Dict with 'sent' and 'failed' counts
        """
        results = {"sent": 0, "failed": 0, "skipped": 0}

        users = await self.get_users_for_digest()
        logger.info(f"Sending digests to {len(users)} users")

        for user in users:
            # Check frequency preference
            frequency = self._get_digest_frequency(user)
            if frequency == "weekly" and datetime.utcnow().weekday() != 0:  # Monday
                results["skipped"] += 1
                continue

            if await self.send_digest_to_user(user):
                results["sent"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Digest sending complete: {results}")
        return results

    async def preview_digest(self, user_id: UUID) -> Dict[str, Any]:
        """Generate a digest preview without sending.

        Args:
            user_id: User ID to preview digest for

        Returns:
            Dict with html_content, matches, and stats
        """
        # Get user
        query = (
            select(User)
            .options(joinedload(User.profile))
            .where(User.id == user_id)
        )
        result = await self.db.execute(query)
        user = result.unique().scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        matches = await self.get_new_matches_for_user(user_id)
        stats = await self.get_digest_stats(user_id)
        html_content = self.generate_digest_html(user, matches, stats)

        return {
            "html_content": html_content,
            "matches_count": len(matches),
            "stats": stats,
            "matches": [
                {
                    "id": str(m.id),
                    "job_title": m.job.title,
                    "company": m.job.company,
                    "score": float(m.score),
                }
                for m in matches
            ],
        }
