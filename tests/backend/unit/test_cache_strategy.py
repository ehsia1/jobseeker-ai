"""
Unit tests for cache strategy with free-tier optimization
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from backend.services.cache_service import HybridCache, InMemoryCache


class TestHybridCache:
    """Test hybrid caching with Redis fallback to memory"""
    
    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing"""
        redis_mock = Mock()
        return HybridCache(redis_client=redis_mock, memory_cache_size=100)
    
    @pytest.mark.asyncio
    async def test_cache_ttl_6_hours(self, cache):
        """Verify 6-hour TTL for aggressive caching"""
        await cache.set("test_key", {"data": "test"}, ttl_hours=6)
        
        # Should exist before expiry
        result = await cache.get("test_key")
        assert result is not None
        assert result["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_redis_fallback_to_memory(self):
        """Test fallback when Redis is unavailable"""
        # Simulate Redis failure
        cache = HybridCache(redis_client=None, memory_cache_size=100)
        
        # Should use memory cache
        await cache.set("test_key", {"data": "test"})
        result = await cache.get("test_key")
        
        assert result is not None
        assert result["data"] == "test"
        assert cache.stats["memory_hits"] == 1
    
    @pytest.mark.asyncio
    async def test_redis_command_limit_handling(self, cache):
        """Test handling of Redis 10K command limit"""
        cache.redis.execute_command = Mock(side_effect=Exception("Rate limit exceeded"))
        
        # Should fallback to memory gracefully
        await cache.set("fallback_key", {"data": "fallback"})
        result = await cache.get("fallback_key")
        
        assert result is not None
        assert cache.stats["redis_errors"] > 0
        assert cache.stats["memory_hits"] > 0


class TestInMemoryCache:
    """Test in-memory cache implementation"""
    
    def test_max_size_limit(self):
        """Test memory cache respects size limits"""
        cache = InMemoryCache(max_size=3)
        
        # Add 4 items, oldest should be evicted
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key4") is not None  # Still exists
        assert len(cache.cache) == 3
    
    def test_ttl_expiration(self):
        """Test TTL expiration in memory cache"""
        cache = InMemoryCache()
        cache.set("temp_key", "temp_value", ttl_seconds=1)
        
        # Should exist immediately
        assert cache.get("temp_key") == "temp_value"
        
        # Mock time passage
        import time
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("temp_key") is None


class TestCacheMetrics:
    """Test cache metrics for monitoring"""
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        cache = HybridCache(redis_client=None)
        
        # Generate hits and misses
        await cache.set("hit_key", "value")
        await cache.get("hit_key")  # Hit
        await cache.get("hit_key")  # Hit
        await cache.get("miss_key")  # Miss
        
        metrics = cache.get_metrics()
        
        assert metrics["total_requests"] == 3
        assert metrics["hits"] == 2
        assert metrics["misses"] == 1
        assert metrics["hit_rate"] == pytest.approx(0.666, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_redis_command_tracking(self):
        """Track Redis command usage for free tier monitoring"""
        redis_mock = Mock()
        redis_mock.get = Mock(return_value=None)
        redis_mock.set = Mock(return_value=True)
        
        cache = HybridCache(redis_client=redis_mock)
        
        # Perform operations
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")
            await cache.get(f"key_{i}")
        
        metrics = cache.get_metrics()
        
        assert metrics["redis_commands_today"] == 200
        assert metrics["redis_remaining"] == 9800  # 10K - 200