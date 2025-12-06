"""
Batch job search system for free tier optimization
Searches all job boards periodically and caches results
Users get instant results from cache instead of real-time searches
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
from collections import defaultdict

from backend.services.cache_service import get_cache, HybridCache
from backend.searchers.searcher_registry import SearcherRegistry
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_


class BatchJobSearcher:
    """
    Batch job searcher that runs periodically to stay within API limits
    Perfect for free tier - searches run in background, users get instant cached results
    """
    
    def __init__(self, cache: Optional[HybridCache] = None):
        self.cache = cache or get_cache()
        self.registry = SearcherRegistry()
        self.search_interval = 30 * 60  # 30 minutes
        self.max_jobs_per_board = 50    # Limit to stay within free tiers
        self.is_running = False
        self.last_search_time = {}
        
        # Popular search terms to pre-cache
        self.popular_searches = [
            ["python", "developer"],
            ["javascript", "react"],
            ["senior", "engineer"],
            ["data", "scientist"],
            ["product", "manager"],
            ["devops", "engineer"],
            ["full", "stack"],
            ["machine", "learning"],
            ["frontend", "developer"],
            ["backend", "developer"],
        ]
        
        # Professions to search
        self.professions = [
            "software_engineer",
            "data_scientist",
            "product_manager",
            "designer",
            "marketing",
        ]
    
    async def run_batch_search(self):
        """
        Main batch search that runs periodically
        Searches all configured job boards and caches results
        """
        if self.is_running:
            print("Batch search already running, skipping...")
            return
        
        self.is_running = True
        start_time = datetime.now()
        total_jobs_found = 0
        
        print(f"Starting batch job search at {start_time}")
        
        try:
            # Search for each profession
            for profession in self.professions:
                profession_jobs = await self._search_profession(profession)
                total_jobs_found += len(profession_jobs)
                
                # Cache by profession
                cache_key = f"batch:profession:{profession}"
                await self.cache.set(cache_key, profession_jobs, "job_search", ttl=3600)
            
            # Search popular keywords
            for keywords in self.popular_searches:
                keyword_jobs = await self._search_keywords(keywords)
                total_jobs_found += len(keyword_jobs)
                
                # Cache by keywords
                cache_key = f"batch:keywords:{':'.join(keywords)}"
                await self.cache.set(cache_key, keyword_jobs, "job_search", ttl=3600)
            
            # Update stats
            await self._update_search_stats(total_jobs_found)
            
            duration = (datetime.now() - start_time).seconds
            print(f"Batch search completed: {total_jobs_found} jobs found in {duration}s")
            
        except Exception as e:
            print(f"Batch search error: {e}")
        finally:
            self.is_running = False
    
    async def _search_profession(self, profession: str) -> List[Dict]:
        """Search jobs for a specific profession"""
        all_jobs = []
        searchers = self.registry.get_searchers_for_profession(profession)
        
        for searcher_class in searchers[:3]:  # Limit to top 3 boards per profession
            board_name = searcher_class.__name__
            
            # Check if we searched this board recently
            if self._should_skip_board(board_name):
                cached = await self._get_cached_board_results(board_name)
                if cached:
                    all_jobs.extend(cached)
                    continue
            
            try:
                # Initialize searcher
                searcher = searcher_class()
                
                # Perform search
                results = await searcher.search({
                    "keywords": [profession.replace("_", " ")],
                    "remote_only": True,
                    "limit": self.max_jobs_per_board
                })
                
                # Process and cache results
                processed = self._process_job_results(results, profession, board_name)
                all_jobs.extend(processed)
                
                # Cache board results
                await self._cache_board_results(board_name, processed)
                
                # Update last search time
                self.last_search_time[board_name] = datetime.now()
                
                # Small delay to avoid rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error searching {board_name} for {profession}: {e}")
                continue
        
        return all_jobs
    
    async def _search_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search jobs for specific keywords"""
        all_jobs = []
        
        # Use only most relevant boards for keywords
        searchers = [
            "RemoteOKSearcher",
            "HackerNewsSearcher", 
            "GitHubJobsSearcher"
        ]
        
        for searcher_name in searchers:
            if self._should_skip_board(searcher_name):
                continue
            
            try:
                # Get searcher class
                searcher_class = self.registry._get_searcher_by_name(searcher_name)
                if not searcher_class:
                    continue
                
                searcher = searcher_class()
                
                # Perform search
                results = await searcher.search({
                    "keywords": keywords,
                    "remote_only": True,
                    "limit": 20  # Smaller limit for keyword searches
                })
                
                processed = self._process_job_results(results, None, searcher_name)
                all_jobs.extend(processed)
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error searching {searcher_name} for {keywords}: {e}")
                continue
        
        return all_jobs
    
    def _should_skip_board(self, board_name: str) -> bool:
        """Check if we should skip searching this board"""
        last_search = self.last_search_time.get(board_name)
        if not last_search:
            return False
        
        time_since_search = (datetime.now() - last_search).seconds
        return time_since_search < self.search_interval
    
    async def _get_cached_board_results(self, board_name: str) -> Optional[List]:
        """Get cached results for a job board"""
        cache_key = f"board_cache:{board_name}"
        return await self.cache.get(cache_key, "job_boards")
    
    async def _cache_board_results(self, board_name: str, results: List):
        """Cache job board results"""
        cache_key = f"board_cache:{board_name}"
        await self.cache.set(cache_key, results, "job_boards", ttl=3600)
    
    def _process_job_results(self, results: List, profession: str, source: str) -> List[Dict]:
        """Process and enrich job results"""
        processed = []
        
        for job in results[:self.max_jobs_per_board]:
            # Add metadata
            job_data = {
                **job,
                "batch_searched_at": datetime.now().isoformat(),
                "source_board": source,
                "profession_match": profession,
                "job_id": self._generate_job_id(job)
            }
            processed.append(job_data)
        
        return processed
    
    def _generate_job_id(self, job: Dict) -> str:
        """Generate unique job ID"""
        unique_str = f"{job.get('title', '')}:{job.get('company', '')}:{job.get('url', '')}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    async def _update_search_stats(self, total_jobs: int):
        """Update search statistics in cache"""
        stats = {
            "last_batch_search": datetime.now().isoformat(),
            "total_jobs_found": total_jobs,
            "boards_searched": len(self.last_search_time),
            "cache_hit_rate": self.cache.memory_cache.get_stats()["hit_rate"]
        }
        
        await self.cache.set("batch_search_stats", stats, "stats", ttl=300)
    
    async def get_cached_jobs(self, query: Dict) -> List[Dict]:
        """
        Get jobs from cache based on query
        This is what users call - returns instant results from batch cache
        """
        # Try exact query match first
        query_key = self._get_query_cache_key(query)
        cached = await self.cache.get(query_key, "job_search")
        if cached:
            return cached
        
        # Try profession-based cache
        profession = query.get("profession")
        if profession:
            cache_key = f"batch:profession:{profession}"
            profession_jobs = await self.cache.get(cache_key, "job_search")
            if profession_jobs:
                # Filter based on query
                filtered = self._filter_jobs_by_query(profession_jobs, query)
                # Cache filtered results
                await self.cache.set(query_key, filtered, "job_search", ttl=1800)
                return filtered
        
        # Try keyword-based cache
        keywords = query.get("keywords", [])
        if keywords:
            # Find best matching cached search
            for cached_keywords in self.popular_searches:
                if any(k in keywords for k in cached_keywords):
                    cache_key = f"batch:keywords:{':'.join(cached_keywords)}"
                    keyword_jobs = await self.cache.get(cache_key, "job_search")
                    if keyword_jobs:
                        filtered = self._filter_jobs_by_query(keyword_jobs, query)
                        await self.cache.set(query_key, filtered, "job_search", ttl=1800)
                        return filtered
        
        # No cache hit - return empty (batch search will populate soon)
        return []
    
    def _get_query_cache_key(self, query: Dict) -> str:
        """Generate cache key for query"""
        query_str = json.dumps(query, sort_keys=True, default=str)
        return f"query:{hashlib.md5(query_str.encode()).hexdigest()}"
    
    def _filter_jobs_by_query(self, jobs: List[Dict], query: Dict) -> List[Dict]:
        """Filter jobs based on query parameters"""
        filtered = jobs
        
        # Filter by remote
        if query.get("remote_only"):
            filtered = [j for j in filtered if j.get("remote", False)]
        
        # Filter by location
        location = query.get("location")
        if location:
            location_lower = location.lower()
            filtered = [j for j in filtered 
                       if location_lower in j.get("location", "").lower() or j.get("remote")]
        
        # Filter by salary
        min_rate = query.get("min_rate")
        if min_rate:
            filtered = [j for j in filtered if j.get("rate_min", 0) >= min_rate]
        
        max_rate = query.get("max_rate")
        if max_rate:
            filtered = [j for j in filtered if j.get("rate_max", float('inf')) <= max_rate]
        
        # Filter by keywords
        keywords = query.get("keywords", [])
        if keywords:
            filtered = self._filter_by_keywords(filtered, keywords)
        
        # Limit results
        limit = query.get("limit", 50)
        return filtered[:limit]
    
    def _filter_by_keywords(self, jobs: List[Dict], keywords: List[str]) -> List[Dict]:
        """Filter jobs by keywords in title or description"""
        filtered = []
        keywords_lower = [k.lower() for k in keywords]
        
        for job in jobs:
            job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
            if any(keyword in job_text for keyword in keywords_lower):
                filtered.append(job)
        
        return filtered


# Background task runner for batch searches
class BatchSearchScheduler:
    """
    Scheduler that runs batch searches periodically
    Designed to work with free tier hosting
    """
    
    def __init__(self):
        self.searcher = BatchJobSearcher()
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the batch search scheduler"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        print("Batch search scheduler started")
    
    async def stop(self):
        """Stop the batch search scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print("Batch search scheduler stopped")
    
    async def _run_scheduler(self):
        """Run batch searches on schedule"""
        while self.running:
            try:
                # Run batch search
                await self.searcher.run_batch_search()
                
                # Wait for next interval (30 minutes)
                await asyncio.sleep(1800)
                
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error


# Global scheduler instance
_scheduler = None

def get_batch_scheduler() -> BatchSearchScheduler:
    """Get or create batch search scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BatchSearchScheduler()
    return _scheduler