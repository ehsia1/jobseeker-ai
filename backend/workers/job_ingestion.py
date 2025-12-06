"""Job ingestion background tasks."""

import asyncio
from typing import List
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.workers.celery_app import celery_app
from backend.database import async_session
from backend.models.job import Job
from backend.parsers import (
    UpworkEmailParser, 
    RemoteOKParser,
    EmailJobParser
)
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task class with database session management."""
    
    def run(self, *args, **kwargs):
        """Override run to handle async database operations."""
        return asyncio.run(self.async_run(*args, **kwargs))
    
    async def async_run(self, *args, **kwargs):
        """Async implementation to be overridden by subclasses."""
        raise NotImplementedError


@celery_app.task(bind=True, base=DatabaseTask)
async def process_email_alerts_task(self):
    """Process email alerts from job platforms."""
    
    logger.info("Starting email alerts processing")
    
    try:
        # Initialize parsers
        parsers = [
            UpworkEmailParser(),
            # LinkedInEmailParser(),  # TODO: Implement
            # IndeedEmailParser(),    # TODO: Implement
        ]
        
        total_jobs_processed = 0
        
        for parser in parsers:
            try:
                logger.info(f"Processing emails with {parser.__class__.__name__}")
                
                # Fetch recent emails
                emails = await parser.fetch_emails(limit=20)
                
                for email_data in emails:
                    try:
                        # Parse jobs from email
                        jobs = await parser.parse(
                            email_data['body'],
                            metadata={
                                'subject': email_data['subject'],
                                'from': email_data['from'],
                                'date': email_data['date']
                            }
                        )
                        
                        # Store jobs in database
                        stored_count = await self._store_jobs(jobs)
                        total_jobs_processed += stored_count
                        
                        logger.info(f"Processed {len(jobs)} jobs from email: {email_data['subject'][:50]}...")
                        
                    except Exception as e:
                        logger.error(f"Error processing email {email_data.get('subject', 'Unknown')}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error with parser {parser.__class__.__name__}: {e}")
                continue
        
        logger.info(f"Email processing complete. Processed {total_jobs_processed} jobs total")
        
        # Trigger matching for active users after ingestion
        if total_jobs_processed > 0:
            match_jobs_task.delay()
        
        return {
            "status": "success",
            "jobs_processed": total_jobs_processed,
            "parsers_used": len(parsers)
        }
        
    except Exception as e:
        logger.error(f"Email processing failed: {e}")
        return {"status": "error", "message": str(e)}
    
    async def _store_jobs(self, jobs: List) -> int:
        """Store parsed jobs in database."""
        
        if not jobs:
            return 0
        
        stored_count = 0
        
        async with async_session() as db:
            try:
                for parsed_job in jobs:
                    # Check if job already exists
                    existing_job = None
                    if parsed_job.source_id:
                        result = await db.execute(
                            select(Job).where(
                                Job.source == parsed_job.source,
                                Job.source_id == parsed_job.source_id
                            )
                        )
                        existing_job = result.scalar_one_or_none()
                    
                    if existing_job:
                        logger.debug(f"Job already exists: {parsed_job.title}")
                        continue
                    
                    # Create new job record
                    job = Job(
                        source=parsed_job.source,
                        source_id=parsed_job.source_id,
                        title=parsed_job.title,
                        company=parsed_job.company,
                        description=parsed_job.description,
                        requirements=parsed_job.requirements or [],
                        skills=parsed_job.skills or [],
                        rate_min=parsed_job.rate_min,
                        rate_max=parsed_job.rate_max,
                        rate_type=parsed_job.rate_type,
                        location=parsed_job.location,
                        remote=parsed_job.remote,
                        hours_per_week=parsed_job.hours_per_week,
                        duration=parsed_job.duration,
                        posted_at=parsed_job.posted_at,
                        expires_at=parsed_job.expires_at,
                        url=parsed_job.url,
                        raw_data=parsed_job.raw_data or {}
                    )
                    
                    db.add(job)
                    stored_count += 1
                
                await db.commit()
                logger.info(f"Stored {stored_count} new jobs in database")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error storing jobs: {e}")
                raise
        
        return stored_count


@celery_app.task(bind=True, base=DatabaseTask)
async def fetch_rss_feeds_task(self):
    """Fetch and process RSS job feeds."""
    
    logger.info("Starting RSS feeds processing")
    
    try:
        # Initialize RSS parsers
        rss_sources = [
            RemoteOKParser(),
            # WeWorkRemotelyParser(),  # TODO: Implement
            # AngelListParser(),       # TODO: Implement
        ]
        
        total_jobs_processed = 0
        
        for parser in rss_sources:
            try:
                logger.info(f"Fetching RSS feed: {parser.feed_url}")
                
                # Fetch and parse RSS feed
                async with parser:
                    jobs = await parser.fetch_and_parse(limit=50)
                
                # Store jobs in database  
                stored_count = await self._store_jobs(jobs)
                total_jobs_processed += stored_count
                
                logger.info(f"Processed {len(jobs)} jobs from {parser.source_name}")
                
            except Exception as e:
                logger.error(f"Error processing RSS feed {parser.source_name}: {e}")
                continue
        
        logger.info(f"RSS processing complete. Processed {total_jobs_processed} jobs total")
        
        # Trigger matching for active users after ingestion
        if total_jobs_processed > 0:
            match_jobs_task.delay()
        
        return {
            "status": "success", 
            "jobs_processed": total_jobs_processed,
            "feeds_processed": len(rss_sources)
        }
        
    except Exception as e:
        logger.error(f"RSS processing failed: {e}")
        return {"status": "error", "message": str(e)}
    
    async def _store_jobs(self, jobs: List) -> int:
        """Store parsed jobs in database (same as email processing)."""
        return await process_email_alerts_task._store_jobs(self, jobs)


@celery_app.task
def ingest_jobs_task():
    """Manual job ingestion trigger (combines email and RSS)."""
    
    logger.info("Manual job ingestion triggered")
    
    # Run both email and RSS processing
    email_result = process_email_alerts_task.delay()
    rss_result = fetch_rss_feeds_task.delay() 
    
    return {
        "status": "triggered",
        "email_task_id": email_result.id,
        "rss_task_id": rss_result.id
    }


# Import match_jobs_task to avoid circular import issues
@celery_app.task
def match_jobs_task():
    """Placeholder for job matching task - implemented in job_matching.py."""
    from backend.workers.job_matching import generate_daily_matches_task
    return generate_daily_matches_task.delay()