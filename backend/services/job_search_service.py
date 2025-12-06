"""Job search service that aggregates from multiple job boards."""

import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from backend.models.user import User, UserProfile
from backend.models.job import Job
from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult
from backend.searchers.searcher_registry import SearcherRegistry
from backend.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


class JobSearchService:
    """Service for searching and aggregating jobs from multiple sources."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.searchers = []  # Will be set dynamically based on profession
        self.matching_service = MatchingService(db)
    
    async def search_for_user(
        self, 
        user: User,
        custom_keywords: Optional[List[str]] = None,
        limit_per_source: int = 20
    ) -> Dict[str, Any]:
        """
        Search for jobs based on user profile.
        
        Args:
            user: User to search for
            custom_keywords: Additional keywords to search
            limit_per_source: Max results per job board
            
        Returns:
            Dictionary with search results and statistics
        """
        # Get user profile
        profile_result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            logger.warning(f"No profile found for user {user.id}")
            return {"error": "User profile not found", "results": []}
        
        # Select searchers based on user's profession
        profession = profile.profession or SearcherRegistry.suggest_profession(profile.skills)
        self.searchers = SearcherRegistry.get_searchers_for_profession(profession)
        logger.info(f"Using {len(self.searchers)} searchers for profession: {profession}")
        
        # Build search query from profile
        query = self._build_search_query(profile, custom_keywords, limit_per_source)
        
        # Search all sources concurrently
        search_tasks = []
        for searcher in self.searchers:
            search_tasks.append(self._search_source(searcher, query))
        
        search_results = await asyncio.gather(*search_tasks)
        
        # Aggregate results
        all_results = []
        source_stats = {}
        
        for searcher, results in zip(self.searchers, search_results):
            source_name = searcher.source_name
            source_stats[source_name] = len(results)
            all_results.extend(results)
        
        # Remove duplicates based on title and company
        unique_results = self._deduplicate_results(all_results)
        
        # Store new jobs in database
        stored_count = await self._store_search_results(unique_results)
        
        # Generate matches for the new jobs
        if stored_count > 0:
            matches_created = await self.matching_service.generate_matches_for_user(user.id)
            logger.info(f"Created {matches_created} matches for user {user.id}")
        
        return {
            "total_results": len(unique_results),
            "stored_jobs": stored_count,
            "source_stats": source_stats,
            "results": [self._serialize_result(r) for r in unique_results[:50]]  # Return top 50
        }
    
    async def search_by_keywords(
        self,
        keywords: List[str],
        profession: Optional[str] = None,
        remote_only: bool = True,
        limit_per_source: int = 20
    ) -> Dict[str, Any]:
        """
        Search for jobs by keywords.
        
        Args:
            keywords: Keywords to search for
            profession: Professional field (e.g., "software_engineer", "marketing")
            remote_only: Only return remote jobs
            limit_per_source: Max results per job board
            
        Returns:
            Dictionary with search results
        """
        # Select searchers based on profession or keywords
        if profession:
            self.searchers = SearcherRegistry.get_searchers_for_profession(profession)
        else:
            # Try to infer profession from keywords
            suggested_profession = SearcherRegistry.suggest_profession(keywords)
            self.searchers = SearcherRegistry.get_searchers_for_profession(suggested_profession)
        
        logger.info(f"Using {len(self.searchers)} searchers for search")
        
        query = SearchQuery(
            keywords=keywords,
            remote_only=remote_only,
            limit=limit_per_source
        )
        
        # Search all sources
        search_tasks = []
        for searcher in self.searchers:
            search_tasks.append(self._search_source(searcher, query))
        
        search_results = await asyncio.gather(*search_tasks)
        
        # Aggregate results
        all_results = []
        source_stats = {}
        
        for searcher, results in zip(self.searchers, search_results):
            source_name = searcher.source_name
            source_stats[source_name] = len(results)
            all_results.extend(results)
        
        # Remove duplicates
        unique_results = self._deduplicate_results(all_results)
        
        return {
            "total_results": len(unique_results),
            "source_stats": source_stats,
            "results": [self._serialize_result(r) for r in unique_results[:100]]
        }
    
    def _build_search_query(
        self,
        profile: UserProfile,
        custom_keywords: Optional[List[str]],
        limit: int
    ) -> SearchQuery:
        """Build search query from user profile."""
        # Extract keywords from skills
        keywords = profile.skills.copy() if profile.skills else []
        
        # Add custom keywords
        if custom_keywords:
            keywords.extend(custom_keywords)
        
        # Remove duplicates
        keywords = list(set(keywords))
        
        # Get preferences
        preferences = profile.preferences or {}
        
        return SearchQuery(
            keywords=keywords[:10],  # Limit to top 10 keywords
            remote_only=preferences.get('remote_only', True),
            min_rate=float(profile.min_rate_usd) if profile.min_rate_usd else None,
            job_type=preferences.get('job_types', [None])[0] if preferences.get('job_types') else None,
            limit=limit
        )
    
    async def _search_source(self, searcher: BaseJobSearcher, query: SearchQuery) -> List[SearchResult]:
        """Search a single source."""
        try:
            async with searcher:
                results = await searcher.search(query)
                return results
        except Exception as e:
            logger.error(f"Error searching {searcher.source_name}: {e}")
            return []
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate jobs based on title and company."""
        seen = set()
        unique = []
        
        for result in results:
            # Create a key from title and company
            key = f"{result.title.lower()[:50]}_{(result.company or '').lower()[:30]}"
            
            if key not in seen:
                seen.add(key)
                unique.append(result)
        
        return unique
    
    async def _store_search_results(self, results: List[SearchResult]) -> int:
        """Store search results in database."""
        stored_count = 0
        
        for result in results:
            try:
                # Check if job already exists
                existing = await self.db.execute(
                    select(Job).where(
                        Job.source == result.source,
                        Job.title == result.title,
                        Job.company == result.company
                    )
                )
                
                if existing.scalar_one_or_none():
                    continue
                
                # Create new job
                job = Job(
                    source=result.source,
                    source_id=result.source_id,
                    title=result.title,
                    company=result.company,
                    description=result.description,
                    requirements=[],  # Could extract from description
                    skills=result.skills or [],
                    rate_min=result.salary_min,
                    rate_max=result.salary_max,
                    rate_type=result.salary_type,
                    location=result.location,
                    remote=result.remote,
                    posted_at=result.posted_date,
                    url=result.url,
                    raw_data=result.raw_data or {}
                )
                
                self.db.add(job)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing job: {e}")
                continue
        
        if stored_count > 0:
            await self.db.commit()
            logger.info(f"Stored {stored_count} new jobs")
        
        return stored_count
    
    def _serialize_result(self, result: SearchResult) -> Dict[str, Any]:
        """Serialize SearchResult for API response."""
        return {
            "source": result.source,
            "title": result.title,
            "company": result.company,
            "description": result.description[:500],  # Truncate
            "url": result.url,
            "location": result.location,
            "remote": result.remote,
            "salary_min": result.salary_min,
            "salary_max": result.salary_max,
            "salary_type": result.salary_type,
            "skills": result.skills,
            "posted_date": result.posted_date.isoformat() if result.posted_date else None,
            "job_type": result.job_type,
            "experience_level": result.experience_level
        }