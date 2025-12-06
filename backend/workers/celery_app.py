"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from backend.config import settings

# Create Celery instance
celery_app = Celery("jobseeker_ai")

# Configure Celery
celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        "backend.workers.job_ingestion.*": {"queue": "ingestion"},
        "backend.workers.job_matching.*": {"queue": "matching"},
        "backend.workers.notifications.*": {"queue": "notifications"},
    },
    
    # Periodic tasks
    beat_schedule={
        # Process email alerts every 15 minutes
        "process-email-alerts": {
            "task": "backend.workers.job_ingestion.process_email_alerts_task",
            "schedule": crontab(minute="*/15"),
        },
        
        # Fetch RSS feeds every 30 minutes  
        "fetch-rss-feeds": {
            "task": "backend.workers.job_ingestion.fetch_rss_feeds_task",
            "schedule": crontab(minute="*/30"),
        },
        
        # Generate job matches for active users daily at 9 AM
        "generate-daily-matches": {
            "task": "backend.workers.job_matching.generate_daily_matches_task",
            "schedule": crontab(hour=9, minute=0),
        },
        
        # Send daily digests at 10 AM
        "send-daily-digests": {
            "task": "backend.workers.notifications.send_daily_digests_task", 
            "schedule": crontab(hour=10, minute=0),
        },
        
        # Cleanup old jobs weekly
        "cleanup-old-jobs": {
            "task": "backend.workers.maintenance.cleanup_old_jobs_task",
            "schedule": crontab(day_of_week=0, hour=2, minute=0),  # Sunday 2 AM
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "backend.workers.job_ingestion",
    "backend.workers.job_matching", 
    "backend.workers.notifications",
    "backend.workers.maintenance",
])