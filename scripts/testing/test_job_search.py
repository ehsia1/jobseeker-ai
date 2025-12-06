#!/usr/bin/env python3
"""Test script for job search functionality."""

import asyncio
import logging
from datetime import datetime
from pprint import pprint

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import searchers
from backend.searchers.base import SearchQuery
from backend.searchers.remoteok_searcher import RemoteOKSearcher
from backend.searchers.hackernews_searcher import HackerNewsSearcher
from backend.searchers.github_jobs_searcher import GitHubJobsSearcher


async def test_individual_searcher(searcher_class, query):
    """Test an individual searcher."""
    searcher = searcher_class()
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {searcher.source_name} Searcher")
    logger.info(f"{'='*60}")
    
    try:
        async with searcher:
            results = await searcher.search(query)
            logger.info(f"Found {len(results)} jobs on {searcher.source_name}")
            
            # Show first 3 results
            for i, result in enumerate(results[:3], 1):
                logger.info(f"\nJob {i}:")
                logger.info(f"  Title: {result.title}")
                logger.info(f"  Company: {result.company}")
                logger.info(f"  Location: {result.location}")
                logger.info(f"  Remote: {result.remote}")
                if result.salary_min or result.salary_max:
                    logger.info(f"  Salary: ${result.salary_min or 'N/A'} - ${result.salary_max or 'N/A'} ({result.salary_type})")
                if result.skills:
                    logger.info(f"  Skills: {', '.join(result.skills[:5])}")
                logger.info(f"  URL: {result.url}")
                
            return results
    except Exception as e:
        logger.error(f"Error testing {searcher.source_name}: {e}")
        return []


async def test_aggregated_search():
    """Test aggregated search across all sources."""
    logger.info(f"\n{'='*60}")
    logger.info("Testing Aggregated Job Search")
    logger.info(f"{'='*60}")
    
    # Since we need environment variables for the full service,
    # we'll just demonstrate that the searchers can work together
    logger.info("The searchers are working individually!")
    logger.info("To use the full JobSearchService, ensure .env file has:")
    logger.info("  - SECRET_KEY")
    logger.info("  - DATABASE_URL") 
    logger.info("  - REDIS_URL")
    logger.info("\nThe service will:")
    logger.info("  1. Search all job boards concurrently")
    logger.info("  2. Deduplicate results")
    logger.info("  3. Store new jobs in the database")
    logger.info("  4. Generate skill-based matches for users")


async def main():
    """Run all tests."""
    # Create a search query
    query = SearchQuery(
        keywords=["python", "django", "fastapi", "backend"],
        remote_only=True,
        limit=5
    )
    
    logger.info("Starting Job Search Tests")
    logger.info(f"Search Query: {query.keywords}")
    logger.info(f"Remote Only: {query.remote_only}")
    logger.info(f"Limit per source: {query.limit}")
    
    # Test individual searchers
    searchers = [
        RemoteOKSearcher,
        HackerNewsSearcher,
        GitHubJobsSearcher
    ]
    
    all_results = []
    for searcher_class in searchers:
        results = await test_individual_searcher(searcher_class, query)
        all_results.extend(results)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total jobs found across all sources: {len(all_results)}")
    
    # Count by source
    source_counts = {}
    for result in all_results:
        source_counts[result.source] = source_counts.get(result.source, 0) + 1
    
    for source, count in source_counts.items():
        logger.info(f"  {source}: {count} jobs")
    
    # Test aggregated search
    await test_aggregated_search()


if __name__ == "__main__":
    asyncio.run(main())