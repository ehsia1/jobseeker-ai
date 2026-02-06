"""Notification background tasks."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from backend.workers.celery_app import celery_app
from backend.database import async_session

logger = logging.getLogger(__name__)

# Thread pool for running async tasks when called from async context
_executor = ThreadPoolExecutor(max_workers=4)


def run_async(coro):
    """
    Run an async coroutine, handling both sync and async calling contexts.

    When called from sync context: uses asyncio.run()
    When called from async context (Celery eager mode in FastAPI): runs in thread pool
    """
    try:
        # Check if there's a running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - we're in sync context, use asyncio.run()
        return asyncio.run(coro)

    # There's a running loop - we're being called from async context
    # Run in a new thread with its own event loop
    import concurrent.futures

    def run_in_thread():
        return asyncio.run(coro)

    future = _executor.submit(run_in_thread)
    try:
        # In eager mode, we need the result immediately
        return future.result(timeout=300)  # 5 minute timeout
    except concurrent.futures.TimeoutError:
        logger.error("Async task timed out after 5 minutes")
        return {"success": False, "error": "Task timed out"}


@celery_app.task
def send_match_notification_task(user_id: str, match_count: int):
    """Send notification about new matches to user."""

    logger.info(f"Sending notification to user {user_id} about {match_count} new matches")

    # TODO: Implement push notifications / Slack notifications
    # For now, matches are included in daily digest

    return {
        "status": "success",
        "user_id": user_id,
        "matches": match_count
    }


@celery_app.task
def send_tracker_briefing_notification_task(
    user_id: str,
    briefing_type: str,
    action_items_count: int
):
    """Send notification about application tracker briefing."""

    logger.info(
        f"Sending tracker briefing notification to user {user_id}: "
        f"{action_items_count} action items"
    )

    # TODO: Implement push notifications

    return {
        "status": "success",
        "user_id": user_id,
        "briefing_type": briefing_type,
        "action_items": action_items_count
    }


# --- Daily Digest Implementation ---


async def _send_daily_digests():
    """Async implementation: Send daily digests to all eligible users."""
    logger.info("Starting daily digest sending")

    try:
        from backend.services.digest_service import DigestService

        async with async_session() as db:
            digest_service = DigestService(db)
            results = await digest_service.send_all_digests()

            logger.info(
                f"Daily digest sending complete: "
                f"{results['sent']} sent, {results['failed']} failed, "
                f"{results.get('skipped', 0)} skipped"
            )

            return {
                "status": "success",
                "sent": results["sent"],
                "failed": results["failed"],
                "skipped": results.get("skipped", 0),
            }

    except Exception as e:
        logger.error(f"Daily digest sending failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task
def send_daily_digests_task():
    """Send daily digest emails to all active users.

    Scheduled to run daily at 10 AM via Celery Beat.
    """
    return run_async(_send_daily_digests())


async def _send_digest_to_user(user_id: str):
    """Async implementation: Send digest to a specific user."""
    logger.info(f"Sending digest to user {user_id}")

    try:
        from uuid import UUID
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        from backend.models.user import User
        from backend.services.digest_service import DigestService

        async with async_session() as db:
            # Get user
            query = (
                select(User)
                .options(joinedload(User.profile))
                .where(User.id == UUID(user_id))
            )
            result = await db.execute(query)
            user = result.unique().scalar_one_or_none()

            if not user:
                logger.error(f"User not found: {user_id}")
                return {"status": "error", "error": "User not found"}

            digest_service = DigestService(db)
            success = await digest_service.send_digest_to_user(user)

            return {
                "status": "success" if success else "failed",
                "user_id": user_id,
            }

    except Exception as e:
        logger.error(f"Failed to send digest to user {user_id}: {e}")
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task
def send_digest_to_user_task(user_id: str):
    """Send digest email to a specific user.

    Can be triggered manually or used for testing.
    """
    return run_async(_send_digest_to_user(user_id))