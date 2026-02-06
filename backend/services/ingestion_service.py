"""Job ingestion service for coordinating data collection."""

import asyncio
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from backend.models.job import Job
from backend.parsers import (
    UpworkEmailParser,
    RemoteOKParser,
    EmailJobParser
)
from backend.parsers.base import ParsedJob
from backend.searchers.base import SearchQuery, SearchResult, BaseJobSearcher
from backend.searchers.searcher_registry import SearcherRegistry

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

    def _search_result_to_parsed_job(self, result: SearchResult) -> ParsedJob:
        """Convert a SearchResult to ParsedJob for storage."""
        return ParsedJob(
            source=result.source,
            source_id=result.source_id,
            title=result.title,
            company=result.company,
            description=result.description or "",
            url=result.url,
            location=result.location,
            remote=result.remote,
            skills=result.skills or [],
            requirements=[],  # SearchResult doesn't have separate requirements
            rate_min=Decimal(str(result.salary_min)) if result.salary_min else None,
            rate_max=Decimal(str(result.salary_max)) if result.salary_max else None,
            rate_type=result.salary_type,
            posted_at=result.posted_date,
            raw_data=result.raw_data or {}
        )

    async def _ingest_from_searcher(
        self,
        searcher: BaseJobSearcher,
        query: SearchQuery
    ) -> Dict[str, Any]:
        """Ingest jobs from a single searcher."""

        source_name = searcher.__class__.__name__
        logger.info(f"Searching jobs from {source_name}")

        try:
            # Run the search
            results = await searcher.search(query)

            if not results:
                logger.info(f"No results from {source_name}")
                return {
                    "source": source_name,
                    "jobs_found": 0,
                    "jobs_stored": 0
                }

            # Convert SearchResults to ParsedJobs
            parsed_jobs = [self._search_result_to_parsed_job(r) for r in results]

            # Store jobs
            jobs_stored = await self._store_jobs(parsed_jobs)

            return {
                "source": source_name,
                "jobs_found": len(results),
                "jobs_stored": jobs_stored
            }

        except Exception as e:
            logger.error(f"Error searching {source_name}: {e}")
            return {
                "source": source_name,
                "jobs_found": 0,
                "jobs_stored": 0,
                "error": str(e)
            }

    async def ingest_from_searchers(
        self,
        keywords: List[str] = None,
        profession: str = None,
        location: str = None,
        remote_only: bool = True,
        limit_per_source: int = 50
    ) -> Dict[str, Any]:
        """
        Run ingestion using job searchers.

        Args:
            keywords: Search keywords (e.g., ["python", "backend"])
            profession: Profession type to get appropriate searchers
            location: Location filter
            remote_only: Only search for remote jobs
            limit_per_source: Max jobs per searcher

        Returns:
            Summary of ingestion results
        """
        logger.info(f"Starting searcher ingestion for profession={profession}, keywords={keywords}")

        # Build search query
        query = SearchQuery(
            keywords=keywords or [],
            location=location,
            remote_only=remote_only,
            limit=limit_per_source
        )

        # Get searchers - either by profession or all available
        if profession:
            searchers = SearcherRegistry.get_searchers_for_profession(profession)
        else:
            # Use a default set of general-purpose searchers
            searchers = SearcherRegistry.get_all_searchers()

        if not searchers:
            logger.warning(f"No searchers found for profession={profession}")
            return {
                "searcher_results": {},
                "total_jobs_found": 0,
                "total_jobs_stored": 0,
                "errors": ["No searchers available for this profession"]
            }

        results = {
            "searcher_results": {},
            "total_jobs_found": 0,
            "total_jobs_stored": 0,
            "errors": []
        }

        # Run all searchers concurrently
        tasks = []
        for searcher in searchers:
            tasks.append(self._ingest_from_searcher(searcher, query))

        searcher_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(searcher_results):
            searcher_name = searchers[i].__class__.__name__

            if isinstance(result, Exception):
                error_msg = f"Error with {searcher_name}: {result}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["searcher_results"][searcher_name] = {
                    "jobs_found": 0,
                    "jobs_stored": 0,
                    "error": str(result)
                }
            else:
                results["searcher_results"][searcher_name] = result
                results["total_jobs_found"] += result.get("jobs_found", 0)
                results["total_jobs_stored"] += result.get("jobs_stored", 0)
                if result.get("error"):
                    results["errors"].append(result["error"])

        logger.info(
            f"Searcher ingestion complete. "
            f"Found {results['total_jobs_found']}, stored {results['total_jobs_stored']}"
        )

        return results

    async def ingest_for_user_profile(
        self,
        user_id: str,
        skills: List[str] = None,
        profession: str = None,
        location: str = None,
        remote_only: bool = True,
        limit_per_source: int = 30
    ) -> Dict[str, Any]:
        """
        Run targeted ingestion based on user profile.

        This is used to find jobs that match a specific user's skills and preferences.
        """
        logger.info(f"Running targeted ingestion for user {user_id}")

        # Use skills as keywords if provided
        keywords = skills[:10] if skills else None  # Limit to top 10 skills

        return await self.ingest_from_searchers(
            keywords=keywords,
            profession=profession,
            location=location,
            remote_only=remote_only,
            limit_per_source=limit_per_source
        )

    async def ingest_all_with_searchers(self, limit_per_source: int = 50) -> Dict[str, Any]:
        """
        Run full ingestion including both parsers and searchers.
        """
        logger.info("Starting full ingestion with parsers and searchers")

        # Run parser-based ingestion
        parser_results = await self.ingest_all_sources(limit_per_source=limit_per_source)

        # Run searcher-based ingestion for general tech jobs
        searcher_results = await self.ingest_from_searchers(
            keywords=["software", "developer", "engineer"],
            remote_only=True,
            limit_per_source=limit_per_source
        )

        return {
            "parser_results": parser_results,
            "searcher_results": searcher_results,
            "total_jobs": (
                parser_results.get("total_jobs", 0) +
                searcher_results.get("total_jobs_stored", 0)
            )
        }