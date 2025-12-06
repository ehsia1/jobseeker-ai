"""Background workers for job processing."""

from backend.workers.celery_app import celery_app
from backend.workers.job_ingestion import ingest_jobs_task, process_email_alerts_task
from backend.workers.job_matching import match_jobs_task, generate_matches_for_user_task

__all__ = [
    "celery_app",
    "ingest_jobs_task",
    "process_email_alerts_task", 
    "match_jobs_task",
    "generate_matches_for_user_task",
]