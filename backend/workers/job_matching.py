"""Job matching background tasks."""

import asyncio
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.workers.celery_app import celery_app
from backend.database import async_session
from backend.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


class MatchingTask(Task):
    """Base task class for matching operations."""
    
    def run(self, *args, **kwargs):
        """Override run to handle async database operations."""
        return asyncio.run(self.async_run(*args, **kwargs))
    
    async def async_run(self, *args, **kwargs):
        """Async implementation to be overridden by subclasses."""
        raise NotImplementedError


@celery_app.task(bind=True, base=MatchingTask)
async def generate_matches_for_user_task(self, user_id: str):
    """Generate job matches for a specific user."""
    
    logger.info(f"Starting match generation for user {user_id}")
    
    try:
        async with async_session() as db:
            matching_service = MatchingService(db)
            
            matches = await matching_service.generate_matches_for_user(
                user_id=user_id,
                limit=30,
                min_score=70.0,
                days_back=7
            )
            
            logger.info(f"Generated {len(matches)} matches for user {user_id}")
            
            # Trigger notification if matches were found
            if matches:
                from backend.workers.notifications import send_match_notification_task
                send_match_notification_task.delay(user_id, len(matches))
            
            return {
                "status": "success",
                "user_id": user_id,
                "matches_created": len(matches)
            }
            
    except Exception as e:
        logger.error(f"Match generation failed for user {user_id}: {e}")
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task(bind=True, base=MatchingTask)
async def generate_daily_matches_task(self):
    """Generate matches for all active users (daily job)."""
    
    logger.info("Starting daily match generation for all users")
    
    try:
        async with async_session() as db:
            matching_service = MatchingService(db)
            
            results = await matching_service.generate_matches_for_all_active_users(
                limit_per_user=20
            )
            
            logger.info(
                f"Daily matching complete: {results['total_matches']} matches "
                f"for {results['successful_users']} users"
            )
            
            return results
            
    except Exception as e:
        logger.error(f"Daily match generation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, base=MatchingTask)
async def recalculate_match_score_task(self, match_id: str):
    """Recalculate score for a specific match."""
    
    logger.info(f"Recalculating score for match {match_id}")
    
    try:
        async with async_session() as db:
            matching_service = MatchingService(db)
            
            updated_match = await matching_service.recalculate_match_score(match_id)
            
            if updated_match:
                logger.info(f"Updated match {match_id} score to {updated_match.score}")
                return {
                    "status": "success",
                    "match_id": match_id,
                    "new_score": float(updated_match.score)
                }
            else:
                return {
                    "status": "error",
                    "message": "Match not found"
                }
                
    except Exception as e:
        logger.error(f"Score recalculation failed for match {match_id}: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task
def match_jobs_task():
    """Trigger matching for all users after job ingestion."""
    
    logger.info("Triggering job matching after ingestion")
    
    # Run matching for all active users
    result = generate_daily_matches_task.delay()
    
    return {
        "status": "triggered",
        "task_id": result.id
    }