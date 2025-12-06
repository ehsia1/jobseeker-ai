"""Job ingestion service for coordinating data collection."""

import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from backend.models.job import Job
from backend.parsers import (
    UpworkEmailParser,
    RemoteOKParser,
    EmailJobParser
)

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for coordinating job data ingestion from multiple sources."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_parsers = [
            UpworkEmailParser(),
        ]
        self.rss_parsers = [
            RemoteOKParser(),
        ]
    
    async def ingest_all_sources(self, limit_per_source: int = 50) -> Dict[str, Any]:
        """Run ingestion from all configured sources."""
        
        logger.info("Starting full ingestion from all sources")
        
        results = {
            "email_results": {},
            "rss_results": {},
            "total_jobs": 0,
            "errors": []
        }
        
        # Process email sources
        for parser in self.email_parsers:
            try:
                result = await self._ingest_from_email_parser(parser, limit_per_source)
                results["email_results"][parser.source_name] = result
                results["total_jobs"] += result.get("jobs_stored", 0)
            except Exception as e:
                error_msg = f"Error with {parser.source_name} email parser: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Process RSS sources
        for parser in self.rss_parsers:
            try:
                result = await self._ingest_from_rss_parser(parser, limit_per_source)
                results["rss_results"][parser.source_name] = result  
                results["total_jobs"] += result.get("jobs_stored", 0)
            except Exception as e:
                error_msg = f"Error with {parser.source_name} RSS parser: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        logger.info(f"Ingestion complete. Total jobs processed: {results['total_jobs']}")
        
        return results
    
    async def _ingest_from_email_parser(self, parser: EmailJobParser, limit: int) -> Dict[str, Any]:
        """Ingest jobs from email parser."""
        
        logger.info(f"Processing emails from {parser.source_name}")
        
        try:
            # Fetch emails
            emails = await parser.fetch_emails(limit=limit)
            
            all_jobs = []
            processed_emails = 0
            
            for email_data in emails:
                try:
                    jobs = await parser.parse(
                        email_data['body'],
                        metadata={
                            'subject': email_data['subject'],
                            'from': email_data['from'], 
                            'date': email_data['date']
                        }
                    )
                    all_jobs.extend(jobs)
                    processed_emails += 1
                    
                except Exception as e:
                    logger.warning(f"Error parsing email '{email_data.get('subject', 'Unknown')}': {e}")
                    continue
            
            # Store all jobs
            jobs_stored = await self._store_jobs(all_jobs)
            
            return {
                "emails_processed": processed_emails,
                "jobs_parsed": len(all_jobs),
                "jobs_stored": jobs_stored,
                "source": parser.source_name
            }
            
        except Exception as e:
            logger.error(f"Email parser {parser.source_name} failed: {e}")
            return {
                "emails_processed": 0,
                "jobs_parsed": 0,
                "jobs_stored": 0,
                "source": parser.source_name,
                "error": str(e)
            }
    
    async def _ingest_from_rss_parser(self, parser, limit: int) -> Dict[str, Any]:
        """Ingest jobs from RSS parser."""
        
        logger.info(f"Processing RSS feed from {parser.source_name}")
        
        try:
            # Fetch RSS feed
            async with parser:
                jobs = await parser.fetch_and_parse(limit=limit)
            
            # Store jobs
            jobs_stored = await self._store_jobs(jobs)
            
            return {
                "jobs_parsed": len(jobs),
                "jobs_stored": jobs_stored,
                "source": parser.source_name,
                "feed_url": parser.feed_url
            }
            
        except Exception as e:
            logger.error(f"RSS parser {parser.source_name} failed: {e}")
            return {
                "jobs_parsed": 0,
                "jobs_stored": 0,
                "source": parser.source_name,
                "error": str(e)
            }
    
    async def _store_jobs(self, jobs: List) -> int:
        """Store parsed jobs in database, avoiding duplicates."""
        
        if not jobs:
            return 0
        
        stored_count = 0
        
        try:
            for parsed_job in jobs:
                # Check for existing job
                existing_job = await self._find_existing_job(parsed_job)
                
                if existing_job:
                    logger.debug(f"Skipping duplicate job: {parsed_job.title}")
                    continue
                
                # Create new job
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
                
                self.db.add(job)
                stored_count += 1
            
            await self.db.commit()
            logger.info(f"Stored {stored_count} new jobs")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error storing jobs: {e}")
            raise
        
        return stored_count
    
    async def _find_existing_job(self, parsed_job) -> Job:
        """Find existing job to avoid duplicates."""
        
        # Primary check: source + source_id
        if parsed_job.source_id:
            result = await self.db.execute(
                select(Job).where(
                    Job.source == parsed_job.source,
                    Job.source_id == parsed_job.source_id
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        
        # Secondary check: URL (if available)
        if parsed_job.url:
            result = await self.db.execute(
                select(Job).where(Job.url == parsed_job.url)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        
        # Tertiary check: title + company similarity (basic)
        if parsed_job.company:
            result = await self.db.execute(
                select(Job).where(
                    Job.title == parsed_job.title,
                    Job.company == parsed_job.company,
                    Job.source == parsed_job.source
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        
        return None
    
    async def test_parsers(self) -> Dict[str, Any]:
        """Test all parsers without storing data."""
        
        logger.info("Testing all parsers")
        
        results = {
            "email_parsers": {},
            "rss_parsers": {},
            "overall_status": "success"
        }
        
        # Test email parsers
        for parser in self.email_parsers:
            try:
                emails = await parser.fetch_emails(limit=5)
                
                test_jobs = []
                for email_data in emails[:2]:  # Test first 2 emails
                    jobs = await parser.parse(
                        email_data['body'],
                        metadata={
                            'subject': email_data['subject'],
                            'from': email_data['from'],
                            'date': email_data['date']
                        }
                    )
                    test_jobs.extend(jobs)
                
                results["email_parsers"][parser.source_name] = {
                    "status": "success",
                    "emails_fetched": len(emails),
                    "jobs_parsed": len(test_jobs),
                    "sample_job": test_jobs[0].__dict__ if test_jobs else None
                }
                
            except Exception as e:
                results["email_parsers"][parser.source_name] = {
                    "status": "error",
                    "error": str(e)
                }
                results["overall_status"] = "partial_failure"
        
        # Test RSS parsers
        for parser in self.rss_parsers:
            try:
                async with parser:
                    jobs = await parser.fetch_and_parse(limit=5)
                
                results["rss_parsers"][parser.source_name] = {
                    "status": "success",
                    "jobs_parsed": len(jobs),
                    "feed_url": parser.feed_url,
                    "sample_job": jobs[0].__dict__ if jobs else None
                }
                
            except Exception as e:
                results["rss_parsers"][parser.source_name] = {
                    "status": "error", 
                    "error": str(e)
                }
                results["overall_status"] = "partial_failure"
        
        return results