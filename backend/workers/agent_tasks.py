"""Agent background tasks for automated job searching and matching."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

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
    # Return immediately with the future - don't block the event loop
    try:
        # In eager mode, we need the result immediately
        return future.result(timeout=300)  # 5 minute timeout
    except concurrent.futures.TimeoutError:
        logger.error("Async task timed out after 5 minutes")
        return {"success": False, "error": "Task timed out"}


# --- Async implementations ---

async def _run_job_radar_for_user(
    user_id: str,
    keywords: Optional[list] = None,
    min_score: float = 40.0,
    generate_proposals: bool = False,
    max_proposals: int = 3
):
    """
    Async implementation: Run Job Radar agent for a specific user.

    Args:
        user_id: User ID to run Job Radar for
        keywords: Optional custom keywords to add to search
        min_score: Minimum match score threshold
        generate_proposals: Whether to generate proposals
        max_proposals: Maximum number of proposals
    """
    logger.info(f"Starting Job Radar task for user {user_id}")

    try:
        from backend.agents.job_radar_agent import JobRadarAgent

        async with async_session() as db:
            agent = JobRadarAgent(db)
            result = await agent.run(
                user_id=user_id,
                keywords=keywords,
                min_score=min_score,
                generate_proposals=generate_proposals,
                max_proposals=max_proposals
            )

            logger.info(
                f"Job Radar completed for user {user_id}: "
                f"{result.get('matches_found', 0)} matches found"
            )

            # Trigger notification if matches were found
            if result.get("success") and result.get("matches_found", 0) > 0:
                from backend.workers.notifications import send_match_notification_task
                send_match_notification_task.delay(
                    user_id,
                    result["matches_found"]
                )

                # Trigger Network Intelligence for new matches (runs in background)
                top_matches = result.get("top_matches", [])
                if top_matches:
                    # Convert match format for event handler
                    matches_for_event = [
                        {
                            "job_id": m.get("job_id"),
                            "company_name": m.get("company"),
                            "title": m.get("title"),
                            "score": m.get("score", 0)
                        }
                        for m in top_matches
                    ]
                    on_new_matches_found(user_id, matches_for_event)

            return result

    except Exception as e:
        logger.error(f"Job Radar task failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def run_job_radar_for_user_task(
    self,
    user_id: str,
    keywords: Optional[list] = None,
    min_score: float = 40.0,
    generate_proposals: bool = False,
    max_proposals: int = 3
):
    """
    Celery task: Run Job Radar agent for a specific user.

    This task can be triggered:
    - On schedule (daily automated runs)
    - On-demand from API
    - Event-driven (after profile/resume updates)
    """
    return run_async(_run_job_radar_for_user(
        user_id=user_id,
        keywords=keywords,
        min_score=min_score,
        generate_proposals=generate_proposals,
        max_proposals=max_proposals
    ))


async def _run_job_radar_for_all(min_score: float = 40.0):
    """
    Async implementation: Run Job Radar for all active users with profiles.

    Only runs for users who have set up their profile and resume.
    """
    logger.info("Starting daily Job Radar run for all users")

    try:
        from sqlalchemy import select, and_
        from backend.models.user import User, UserProfile

        results = {
            "total_users": 0,
            "successful_runs": 0,
            "total_matches": 0,
            "user_results": []
        }

        async with async_session() as db:
            # Get users with profiles
            query = select(User).join(
                UserProfile,
                User.id == UserProfile.user_id
            ).where(
                and_(
                    User.is_active == True,
                    UserProfile.skills != None  # Has skills configured
                )
            )

            result = await db.execute(query)
            users = result.scalars().all()
            results["total_users"] = len(users)

            logger.info(f"Found {len(users)} active users with profiles")

            # Run Job Radar for each user (limit concurrent runs)
            for user in users:
                try:
                    from backend.agents.job_radar_agent import JobRadarAgent

                    agent = JobRadarAgent(db)
                    user_result = await agent.run(
                        user_id=str(user.id),
                        min_score=min_score,
                        generate_proposals=False  # Skip proposals for batch runs
                    )

                    if user_result.get("success"):
                        results["successful_runs"] += 1
                        results["total_matches"] += user_result.get("matches_found", 0)

                    results["user_results"].append({
                        "user_id": str(user.id),
                        "success": user_result.get("success", False),
                        "matches": user_result.get("matches_found", 0)
                    })

                except Exception as e:
                    logger.error(f"Job Radar failed for user {user.id}: {e}")
                    results["user_results"].append({
                        "user_id": str(user.id),
                        "success": False,
                        "error": str(e)
                    })

        logger.info(
            f"Daily Job Radar complete: {results['successful_runs']}/{results['total_users']} "
            f"successful, {results['total_matches']} total matches"
        )

        return results

    except Exception as e:
        logger.error(f"Daily Job Radar batch failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True)
def run_job_radar_for_all_task(self, min_score: float = 40.0):
    """
    Celery task: Run Job Radar for all active users with profiles.

    This is scheduled to run daily to proactively find new job matches.
    """
    return run_async(_run_job_radar_for_all(min_score=min_score))


async def _recalculate_matches_for_user(user_id: str, trigger: str = "manual"):
    """
    Async implementation: Recalculate all job match scores for a user.

    Args:
        user_id: User ID to recalculate matches for
        trigger: What triggered this recalculation (for logging)
    """
    logger.info(f"Recalculating matches for user {user_id} (trigger: {trigger})")

    try:
        from sqlalchemy import select
        from backend.models.job import JobMatch
        from backend.models.user import UserProfile
        from backend.services.scoring_service import ScoringService
        from backend.services.embedding_service import EmbeddingService

        updated_count = 0
        errors = []

        async with async_session() as db:
            # Get user profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile:
                return {
                    "success": False,
                    "error": "User profile not found",
                    "user_id": user_id
                }

            # Get all matches for user
            matches_result = await db.execute(
                select(JobMatch).where(JobMatch.user_id == user_id)
            )
            matches = matches_result.scalars().all()

            logger.info(f"Found {len(matches)} matches to recalculate for user {user_id}")

            # Initialize scoring service
            embedding_service = EmbeddingService()
            scoring_service = ScoringService(embedding_service)

            # Recalculate each match
            for match in matches:
                try:
                    # Get the job
                    from backend.models.job import Job
                    job_result = await db.execute(
                        select(Job).where(Job.id == match.job_id)
                    )
                    job = job_result.scalar_one_or_none()

                    if job:
                        breakdown = scoring_service.score_job(job, profile)
                        match.score = breakdown.total_score
                        match.score_breakdown = breakdown.to_dict()
                        match.explanation = scoring_service.generate_explanation(
                            job, profile, breakdown
                        )
                        updated_count += 1

                except Exception as e:
                    errors.append(f"Match {match.id}: {str(e)}")
                    logger.warning(f"Failed to recalculate match {match.id}: {e}")

            await db.commit()

        logger.info(
            f"Match recalculation complete for user {user_id}: "
            f"{updated_count} updated, {len(errors)} errors"
        )

        return {
            "success": len(errors) == 0,
            "user_id": user_id,
            "trigger": trigger,
            "matches_updated": updated_count,
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Match recalculation failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def recalculate_matches_for_user_task(self, user_id: str, trigger: str = "manual"):
    """
    Celery task: Recalculate all job match scores for a user.

    Triggered when:
    - Resume is uploaded/updated
    - Profile preferences change
    - Skills are updated
    """
    return run_async(_recalculate_matches_for_user(user_id=user_id, trigger=trigger))


async def _sync_user_profile_from_resume(user_id: str):
    """
    Async implementation: Sync user profile skills and experience from their resume.

    This enables better job matching based on actual resume content.
    """
    logger.info(f"Syncing profile from resume for user {user_id}")

    try:
        from sqlalchemy import select
        from backend.models.user import User, UserProfile
        from backend.models.resume import Resume

        async with async_session() as db:
            # Get user's resume
            resume_result = await db.execute(
                select(Resume).where(Resume.user_id == user_id)
            )
            resume = resume_result.scalar_one_or_none()

            if not resume:
                return {
                    "success": False,
                    "error": "No resume found",
                    "user_id": user_id
                }

            # Get or create profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile:
                from uuid import uuid4
                profile = UserProfile(
                    id=uuid4(),
                    user_id=user_id,
                    skills=[],
                    preferences={}
                )
                db.add(profile)

            # Sync skills from resume (merge, don't replace)
            resume_skills = set(resume.skills or [])
            profile_skills = set(profile.skills or [])
            merged_skills = list(profile_skills | resume_skills)
            profile.skills = merged_skills

            # Sync experience years
            if resume.total_experience_years and resume.total_experience_years > 0:
                profile.experience_years = resume.total_experience_years

            # Sync certifications
            if resume.certifications:
                profile.certifications = resume.certifications

            await db.commit()

            logger.info(
                f"Profile synced for user {user_id}: "
                f"{len(merged_skills)} skills, "
                f"{profile.experience_years or 0} years experience"
            )

            return {
                "success": True,
                "user_id": user_id,
                "skills_count": len(merged_skills),
                "experience_years": profile.experience_years
            }

    except Exception as e:
        logger.error(f"Profile sync failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def sync_user_profile_from_resume_task(self, user_id: str):
    """
    Celery task: Sync user profile skills and experience from their resume.

    Called after resume upload to ensure profile stays in sync.
    """
    return run_async(_sync_user_profile_from_resume(user_id=user_id))


# Convenience functions for event-driven triggers


def on_resume_updated(user_id: str):
    """
    Event handler: Called when a user's resume is updated.

    Triggers (in production with Celery workers):
    1. Sync profile from resume
    2. Recalculate existing match scores
    3. Run Job Radar to find new matches

    Note: In eager mode (local dev), these tasks are skipped because
    async DB connections don't work across event loops. The individual
    tasks can still be tested directly via the API.
    """
    from backend.config import settings

    logger.info(f"Resume updated event triggered for user {user_id}")

    if settings.celery_eager_mode:
        # In eager mode, async DB sessions don't work in separate threads/loops
        # Log the event but skip task execution - users can test tasks directly
        logger.info(
            f"[EAGER MODE] Resume update event logged for user {user_id}. "
            "Background tasks skipped - test via API endpoints directly."
        )
        return {"status": "logged", "mode": "eager", "user_id": user_id}

    # Production mode: run via Celery broker
    from celery import chain

    logger.info(f"Queueing resume update task chain for user {user_id}")
    workflow = chain(
        sync_user_profile_from_resume_task.si(user_id),
        recalculate_matches_for_user_task.si(user_id, trigger="resume_update"),
        run_job_radar_for_user_task.si(user_id, min_score=40.0)
    )
    return workflow.delay()


def on_profile_updated(user_id: str):
    """
    Event handler: Called when user profile preferences change.

    Triggers (in production with Celery workers):
    1. Recalculate existing match scores
    2. Run Job Radar to find new matches based on updated preferences

    Note: In eager mode (local dev), these tasks are skipped because
    async DB connections don't work across event loops. The individual
    tasks can still be tested directly via the API.
    """
    from backend.config import settings

    logger.info(f"Profile updated event triggered for user {user_id}")

    if settings.celery_eager_mode:
        # In eager mode, async DB sessions don't work in separate threads/loops
        # Log the event but skip task execution - users can test tasks directly
        logger.info(
            f"[EAGER MODE] Profile update event logged for user {user_id}. "
            "Background tasks skipped - test via API endpoints directly."
        )
        return {"status": "logged", "mode": "eager", "user_id": user_id}

    # Production mode: run via Celery broker
    from celery import chain

    logger.info(f"Queueing profile update task chain for user {user_id}")
    workflow = chain(
        recalculate_matches_for_user_task.si(user_id, trigger="profile_update"),
        run_job_radar_for_user_task.si(user_id, min_score=40.0)
    )
    return workflow.delay()


# --- Application Tracker Tasks ---


async def _run_application_tracker_for_user(
    user_id: str,
    briefing_type: str = "daily"
):
    """
    Async implementation: Run Application Tracker briefing for a user.

    Args:
        user_id: User ID to generate briefing for
        briefing_type: Type of briefing (daily, weekly, full)
    """
    logger.info(f"Starting Application Tracker briefing for user {user_id}")

    try:
        from backend.agents.application_tracker_agent import ApplicationTrackerAgent

        async with async_session() as db:
            agent = ApplicationTrackerAgent(db)
            result = await agent.run(
                user_id=user_id,
                briefing_type=briefing_type
            )

            logger.info(
                f"Application Tracker completed for user {user_id}: "
                f"{len(result.get('action_items', []))} action items"
            )

            # Send notification if there are action items
            if result.get("success") and result.get("action_items"):
                from backend.workers.notifications import send_tracker_briefing_notification_task
                try:
                    send_tracker_briefing_notification_task.delay(
                        user_id,
                        briefing_type,
                        len(result["action_items"])
                    )
                except Exception as e:
                    logger.warning(f"Failed to send tracker notification: {e}")

            return result

    except Exception as e:
        logger.error(f"Application Tracker failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def run_application_tracker_for_user_task(
    self,
    user_id: str,
    briefing_type: str = "daily"
):
    """
    Celery task: Run Application Tracker briefing for a user.

    Triggered:
    - On schedule (daily morning briefings)
    - On-demand from API
    """
    return run_async(_run_application_tracker_for_user(
        user_id=user_id,
        briefing_type=briefing_type
    ))


async def _run_application_tracker_for_all(briefing_type: str = "daily"):
    """
    Async implementation: Run Application Tracker for all active users.

    Only runs for users who have active job applications.
    """
    logger.info(f"Starting {briefing_type} Application Tracker for all users")

    try:
        from sqlalchemy import select, and_, func
        from backend.models.user import User
        from backend.models.job import JobMatch

        results = {
            "total_users": 0,
            "successful_runs": 0,
            "total_action_items": 0,
            "user_results": []
        }

        async with async_session() as db:
            # Get users with active applications (matches with applied status)
            query = select(User).where(
                User.is_active == True
            ).join(
                JobMatch,
                User.id == JobMatch.user_id
            ).where(
                JobMatch.status.in_(["applied", "interviewing", "saved"])
            ).distinct()

            result = await db.execute(query)
            users = result.scalars().all()
            results["total_users"] = len(users)

            logger.info(f"Found {len(users)} users with active applications")

            for user in users:
                try:
                    from backend.agents.application_tracker_agent import ApplicationTrackerAgent

                    agent = ApplicationTrackerAgent(db)
                    user_result = await agent.run(
                        user_id=str(user.id),
                        briefing_type=briefing_type
                    )

                    if user_result.get("success"):
                        results["successful_runs"] += 1
                        action_count = len(user_result.get("action_items", []))
                        results["total_action_items"] += action_count

                    results["user_results"].append({
                        "user_id": str(user.id),
                        "success": user_result.get("success", False),
                        "action_items": len(user_result.get("action_items", []))
                    })

                except Exception as e:
                    logger.error(f"Application Tracker failed for user {user.id}: {e}")
                    results["user_results"].append({
                        "user_id": str(user.id),
                        "success": False,
                        "error": str(e)
                    })

        logger.info(
            f"Daily Application Tracker complete: {results['successful_runs']}/{results['total_users']} "
            f"successful, {results['total_action_items']} total action items"
        )

        return results

    except Exception as e:
        logger.error(f"Daily Application Tracker batch failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True)
def run_application_tracker_for_all_task(self, briefing_type: str = "daily"):
    """
    Celery task: Run Application Tracker for all users with active applications.

    Scheduled to run daily at 9 AM to provide morning briefings.
    """
    return run_async(_run_application_tracker_for_all(briefing_type=briefing_type))


# --- Cover Letter Pre-generation Tasks ---


async def _generate_cover_letter_for_job(
    user_id: str,
    job_id: str,
    style: str = "modern"
):
    """
    Async implementation: Pre-generate a cover letter for a saved job.

    Args:
        user_id: User ID
        job_id: Job ID to generate cover letter for
        style: Cover letter style
    """
    logger.info(f"Pre-generating cover letter for user {user_id}, job {job_id}")

    try:
        from backend.agents.cover_letter_agent import CoverLetterAgent

        async with async_session() as db:
            agent = CoverLetterAgent(db)
            result = await agent.run(
                user_id=user_id,
                job_id=job_id,
                style=style
            )

            if result.get("success"):
                logger.info(f"Cover letter pre-generated for job {job_id}")
            else:
                logger.warning(f"Cover letter generation failed: {result.get('error')}")

            return result

    except Exception as e:
        logger.error(f"Cover letter pre-generation failed: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "job_id": job_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def generate_cover_letter_for_job_task(
    self,
    user_id: str,
    job_id: str,
    style: str = "modern"
):
    """
    Celery task: Pre-generate a cover letter when a job is saved.
    """
    return run_async(_generate_cover_letter_for_job(
        user_id=user_id,
        job_id=job_id,
        style=style
    ))


# --- Network Intelligence Tasks ---


async def _run_network_intelligence_for_match(
    user_id: str,
    job_id: str,
    company_name: str,
    job_title: Optional[str] = None
):
    """
    Async implementation: Run Network Intelligence for a job match.

    Args:
        user_id: User ID
        job_id: Job ID the match is for
        company_name: Target company name
        job_title: Optional job title/role
    """
    logger.info(f"Running Network Intelligence for user {user_id}, company {company_name}")

    try:
        from backend.agents.network_intelligence_agent import NetworkIntelligenceAgent

        async with async_session() as db:
            agent = NetworkIntelligenceAgent(db)
            result = await agent.run(
                user_id=user_id,
                target_company=company_name,
                target_role=job_title,
                networking_goals=["Build connections at target company", "Learn about hiring process"]
            )

            if result.get("success"):
                logger.info(f"Network Intelligence completed for {company_name}")
            else:
                logger.warning(f"Network Intelligence failed: {result.get('error')}")

            return result

    except Exception as e:
        logger.error(f"Network Intelligence failed: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "job_id": job_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def run_network_intelligence_for_match_task(
    self,
    user_id: str,
    job_id: str,
    company_name: str,
    job_title: Optional[str] = None
):
    """
    Celery task: Run Network Intelligence when new high-quality matches are found.
    """
    return run_async(_run_network_intelligence_for_match(
        user_id=user_id,
        job_id=job_id,
        company_name=company_name,
        job_title=job_title
    ))


# --- Additional Event Handlers ---


def on_job_saved(user_id: str, job_id: str):
    """
    Event handler: Called when a user saves a job.

    Triggers:
    1. Pre-generate a cover letter for the saved job
    """
    from backend.config import settings

    logger.info(f"Job saved event triggered for user {user_id}, job {job_id}")

    if settings.celery_eager_mode:
        logger.info(
            f"[EAGER MODE] Job saved event logged for user {user_id}. "
            "Background tasks skipped - test via API endpoints directly."
        )
        return {"status": "logged", "mode": "eager", "user_id": user_id, "job_id": job_id}

    # Queue cover letter pre-generation
    logger.info(f"Queueing cover letter pre-generation for job {job_id}")
    return generate_cover_letter_for_job_task.delay(user_id, job_id)


def on_new_matches_found(user_id: str, matches: list):
    """
    Event handler: Called when Job Radar finds new high-quality matches.

    Triggers:
    1. Run Network Intelligence for top matches (score >= 80)

    Args:
        user_id: User ID
        matches: List of match dicts with job_id, company_name, title, score
    """
    from backend.config import settings

    logger.info(f"New matches event triggered for user {user_id}: {len(matches)} matches")

    if settings.celery_eager_mode:
        logger.info(
            f"[EAGER MODE] New matches event logged for user {user_id}. "
            "Background tasks skipped - test via API endpoints directly."
        )
        return {"status": "logged", "mode": "eager", "user_id": user_id, "matches": len(matches)}

    # Run Network Intelligence for top matches (score >= 80)
    top_matches = [m for m in matches if m.get("score", 0) >= 80][:3]  # Limit to top 3

    if not top_matches:
        logger.info("No top matches (score >= 80) to run Network Intelligence for")
        return {"status": "skipped", "reason": "no_top_matches"}

    logger.info(f"Queueing Network Intelligence for {len(top_matches)} top matches")

    results = []
    for match in top_matches:
        result = run_network_intelligence_for_match_task.delay(
            user_id,
            match.get("job_id"),
            match.get("company_name", "Unknown Company"),
            match.get("title")
        )
        results.append(result)

    return {"status": "queued", "tasks": len(results)}
