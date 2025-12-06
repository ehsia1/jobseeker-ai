"""
Aggressive caching service for free tier optimization
Minimizes database queries and API calls to stay within limits
"""

import json
import hashlib
from typing import Any, Optional, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from collections import OrderedDict


class InMemoryCache:
    """Simple in-memory LRU cache for when Redis is not available"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            value, expiry = self.cache[key]
            
            if expiry and datetime.now() > expiry:
                del self.cache[key]
                self.misses += 1
                return None
            
            self.hits += 1
            return value
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        expiry = None
        if ttl_seconds:
            expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        
        self.cache[key] = (value, expiry)
        self.cache.move_to_end(key)
        
        # Remove oldest if over size limit
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        self.cache.clear()
    
    def get_stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "size": len(self.cache),
            "max_size": self.max_size
        }


class HybridCache:
    """
    Hybrid caching system that uses Redis if available, falls back to memory
    Optimized for free tier limits
    """
    
    def __init__(self, redis_client=None, memory_cache_size: int = 1000):
        self.redis = redis_client
        self.memory_cache = InMemoryCache(max_size=memory_cache_size)
        self.use_redis = redis_client is not None
        
        # Cache TTLs optimized for free tier
        self.ttls = {
            "job_search": 6 * 3600,      # 6 hours - jobs don't update that often
            "job_details": 24 * 3600,     # 24 hours - static data
            "user_profile": 12 * 3600,    # 12 hours
            "job_boards": 3600,           # 1 hour - board availability
            "scoring_result": 3 * 3600,   # 3 hours - scored results
            "api_response": 1800,         # 30 minutes - API responses
            "stats": 300,                 # 5 minutes - statistics
        }
    
    async def get(self, key: str, category: str = "default") -> Optional[Any]:
        """Get value from cache (checks memory first, then Redis)"""
        
        # Always check memory cache first (free and fast)
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Check Redis if available
        if self.use_redis:
            try:
                redis_value = await self.redis.get(key)
                if redis_value:
                    value = json.loads(redis_value)
                    # Store in memory cache for faster access
                    self.memory_cache.set(key, value, self.ttls.get(category, 3600))
                    return value
            except Exception as e:
                print(f"Redis error: {e}, falling back to memory cache")
                self.use_redis = False
        
        return None
    
    async def set(self, key: str, value: Any, category: str = "default", ttl: Optional[int] = None):
        """Set value in cache (both memory and Redis if available)"""
        
        ttl = ttl or self.ttls.get(category, 3600)
        
        # Always set in memory cache
        self.memory_cache.set(key, value, ttl)
        
        # Set in Redis if available
        if self.use_redis:
            try:
                await self.redis.set(
                    key, 
                    json.dumps(value, default=str), 
                    ex=ttl
                )
            except Exception as e:
                print(f"Redis error: {e}, data cached in memory only")
    
    async def delete(self, key: str):
        """Delete from both caches"""
        self.memory_cache.delete(key)
        if self.use_redis:
            try:
                await self.redis.delete(key)
            except:
                pass
    
    def get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()


def cache_result(category: str = "default", ttl: Optional[int] = None):
    """
    Decorator for caching function results
    Optimized for free tier with aggressive caching
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get or create cache instance
            cache = kwargs.pop("_cache", None) or HybridCache()
            
            # Generate cache key
            cache_key = f"{func.__name__}:{cache.get_cache_key(*args, **kwargs)}"
            
            # Check cache first
            cached_result = await cache.get(cache_key, category)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(cache_key, result, category, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use memory cache only
            cache = InMemoryCache()
            cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl or 3600)
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class CachedJobSearchService:
    """
    Job search service with aggressive caching for free tier
    """
    
    def __init__(self, cache: HybridCache):
        self.cache = cache
        self.last_full_search = {}
    
    @cache_result(category="job_search", ttl=6*3600)
    async def search_jobs(self, keywords: list, location: str = None, remote_only: bool = True):
        """
        Cached job search - results cached for 6 hours
        This dramatically reduces API calls to job boards
        """
        # This will only execute if not in cache
        from backend.searchers.searcher_registry import SearcherRegistry
        
        registry = SearcherRegistry()
        all_results = []
        
        # Search only changed job boards (optimize API calls)
        for searcher_class in registry.get_searchers_for_profession("software_engineer"):
            board_key = f"last_search:{searcher_class.__name__}"
            last_searched = await self.cache.get(board_key, "job_boards")
            
            # Skip if searched recently (within 30 minutes)
            if last_searched:
                last_time = datetime.fromisoformat(last_searched)
                if datetime.now() - last_time < timedelta(minutes=30):
                    # Use cached results for this board
                    cached_board_results = await self.cache.get(
                        f"board_results:{searcher_class.__name__}", 
                        "job_boards"
                    )
                    if cached_board_results:
                        all_results.extend(cached_board_results)
                        continue
            
            # Search this board
            try:
                searcher = searcher_class()
                results = await searcher.search({
                    "keywords": keywords,
                    "location": location,
                    "remote_only": remote_only,
                    "limit": 20  # Limit results per board (free tier optimization)
                })
                
                all_results.extend(results)
                
                # Cache board results
                await self.cache.set(
                    f"board_results:{searcher_class.__name__}",
                    results,
                    "job_boards"
                )
                await self.cache.set(
                    board_key,
                    datetime.now().isoformat(),
                    "job_boards"
                )
            except Exception as e:
                print(f"Error searching {searcher_class.__name__}: {e}")
                continue
        
        return all_results
    
    async def get_cached_or_search(self, query: dict) -> list:
        """
        Smart caching that checks multiple cache levels
        """
        # Generate query hash
        query_hash = hashlib.md5(json.dumps(query, sort_keys=True).encode()).hexdigest()
        
        # Check if we have recent results for this exact query
        cache_key = f"search:{query_hash}"
        cached = await self.cache.get(cache_key, "job_search")
        
        if cached:
            return cached
        
        # Check if we have similar query results we can filter
        similar_key = f"search_broad:{query.get('keywords', [''])[0]}"
        broad_results = await self.cache.get(similar_key, "job_search")
        
        if broad_results:
            # Filter broad results based on specific query
            filtered = self._filter_jobs(broad_results, query)
            await self.cache.set(cache_key, filtered, "job_search", ttl=3600)
            return filtered
        
        # No cache hit, perform search
        results = await self.search_jobs(
            keywords=query.get("keywords", []),
            location=query.get("location"),
            remote_only=query.get("remote_only", True)
        )
        
        # Cache results at multiple levels
        await self.cache.set(cache_key, results, "job_search")
        await self.cache.set(similar_key, results, "job_search")
        
        return results
    
    def _filter_jobs(self, jobs: list, query: dict) -> list:
        """Filter jobs based on query criteria"""
        filtered = jobs
        
        if query.get("remote_only"):
            filtered = [j for j in filtered if j.get("remote")]
        
        if query.get("min_rate"):
            filtered = [j for j in filtered if j.get("rate_min", 0) >= query["min_rate"]]
        
        if query.get("location"):
            location = query["location"].lower()
            filtered = [j for j in filtered if location in j.get("location", "").lower()]
        
        return filtered[:query.get("limit", 50)]


# Global cache instance
_cache_instance = None

def get_cache() -> HybridCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        # Try to connect to Redis if available
        redis_client = None
        try:
            from backend.config_free import settings
            if settings.redis_url:
                import redis.asyncio as redis
                redis_client = redis.from_url(settings.redis_url)
        except:
            pass
        
        _cache_instance = HybridCache(redis_client=redis_client)
    
    return _cache_instance