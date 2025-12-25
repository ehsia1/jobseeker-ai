"""Background workers for job processing."""

from backend.workers.celery_app import celery_app
from backend.workers.job_ingestion import ingest_jobs_task, process_email_alerts_task
from backend.workers.job_matching import match_jobs_task, generate_matches_for_user_task
from backend.workers.agent_tasks import (
    run_job_radar_for_user_task,
    run_job_radar_for_all_task,
    recalculate_matches_for_user_task,
    sync_user_profile_from_resume_task,
    on_resume_updated,
    on_profile_updated,
)

__all__ = [
    "celery_app",
    "ingest_jobs_task",
    "process_email_alerts_task",
    "match_jobs_task",
    "generate_matches_for_user_task",
    # Agent tasks
    "run_job_radar_for_user_task",
    "run_job_radar_for_all_task",
    "recalculate_matches_for_user_task",
    "sync_user_profile_from_resume_task",
    "on_resume_updated",
    "on_profile_updated",
]