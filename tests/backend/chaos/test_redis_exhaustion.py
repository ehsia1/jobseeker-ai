"""
Chaos test for Redis command exhaustion (10K daily limit on Upstash free tier)
"""
import asyncio
import pytest
from unittest.mock import Mock, patch
from backend.services.cache_service import HybridCache


class TestRedisExhaustion:
    """Test system behavior when Redis hits free tier limits"""
    
    @pytest.mark.asyncio
    async def test_redis_10k_command_limit(self):
        """Simulate hitting the 10K daily command limit"""
        redis_mock = Mock()
        command_count = 0
        
        def track_commands(*args, **kwargs):
            nonlocal command_count
            command_count += 1
            if command_count > 10000:
                raise Exception("ERR max daily request limit exceeded")
            return b"OK"
        
        redis_mock.execute_command = Mock(side_effect=track_commands)
        cache = HybridCache(redis_client=redis_mock)
        
        # Simulate 9500 operations (95% of limit)
        for i in range(9500):
            await cache.set(f"key_{i}", f"value_{i}")
        
        assert command_count == 9500
        assert cache.stats["redis_errors"] == 0
        
        # Continue to 10K limit
        for i in range(9500, 10000):
            await cache.set(f"key_{i}", f"value_{i}")
        
        assert command_count == 10000
        
        # Operations beyond limit should use memory cache
        for i in range(10000, 10100):
            await cache.set(f"overflow_{i}", f"value_{i}")
            result = await cache.get(f"overflow_{i}")
            assert result == f"value_{i}"  # Should work via memory
        
        # Verify fallback to memory
        assert cache.stats["redis_errors"] > 0
        assert cache.stats["memory_hits"] > 0
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_at_95_percent(self):
        """Test system starts using memory cache at 95% Redis usage"""
        cache = HybridCache(redis_client=Mock())
        
        # Mock Redis command counter
        cache.redis_commands_today = 9500  # 95% of 10K
        
        # Should prefer memory cache when near limit
        await cache.set("critical_key", "critical_value")
        
        # Verify it used memory instead of Redis
        assert cache.stats["memory_writes"] > 0
    
    @pytest.mark.asyncio
    async def test_redis_recovery_after_midnight(self):
        """Test Redis recovers after daily limit reset"""
        redis_mock = Mock()
        cache = HybridCache(redis_client=redis_mock)
        
        # Simulate exhausted Redis
        cache.redis_commands_today = 10000
        cache.redis_exhausted = True
        
        # Simulate midnight reset
        cache.reset_daily_limits()
        
        # Should be able to use Redis again
        assert cache.redis_commands_today == 0
        assert cache.redis_exhausted is False
        
        # Operations should use Redis again
        await cache.set("post_reset", "value")
        redis_mock.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_cache_performance_during_fallback(self):
        """Ensure performance doesn't degrade during fallback"""
        import time
        
        # Create cache with failed Redis
        cache = HybridCache(redis_client=None)
        
        start_time = time.time()
        
        # Perform 1000 operations using only memory
        for i in range(1000):
            await cache.set(f"perf_key_{i}", f"value_{i}")
            await cache.get(f"perf_key_{i}")
        
        duration = time.time() - start_time
        
        # Should complete in under 1 second even without Redis
        assert duration < 1.0, f"Operations took {duration}s, exceeds 1s limit"
    
    @pytest.mark.asyncio
    async def test_monitoring_metrics_during_exhaustion(self):
        """Test monitoring metrics accurately reflect Redis exhaustion"""
        redis_mock = Mock()
        command_count = 0
        
        def count_commands(*args, **kwargs):
            nonlocal command_count
            command_count += 1
            if command_count > 10000:
                raise Exception("Rate limit exceeded")
            return b"OK"
        
        redis_mock.execute_command = Mock(side_effect=count_commands)
        cache = HybridCache(redis_client=redis_mock)
        
        # Perform operations
        for i in range(100):
            await cache.set(f"monitor_{i}", f"value_{i}")
        
        metrics = cache.get_metrics()
        
        assert metrics["redis_commands_today"] == 100
        assert metrics["redis_remaining"] == 9900
        assert metrics["redis_percentage_used"] == 1.0
        assert metrics["fallback_active"] is False
        
        # Exhaust Redis
        for i in range(100, 10100):
            try:
                await cache.set(f"exhaust_{i}", f"value_{i}")
            except:
                pass
        
        metrics = cache.get_metrics()
        
        assert metrics["redis_commands_today"] >= 10000
        assert metrics["redis_remaining"] == 0
        assert metrics["redis_percentage_used"] == 100.0
        assert metrics["fallback_active"] is True


class TestBatchOperationOptimization:
    """Test batch operations to minimize Redis commands"""
    
    @pytest.mark.asyncio
    async def test_batch_set_operations(self):
        """Test batching multiple sets into single pipeline"""
        redis_mock = Mock()
        pipeline_mock = Mock()
        redis_mock.pipeline = Mock(return_value=pipeline_mock)
        
        cache = HybridCache(redis_client=redis_mock)
        
        # Batch set operation
        items = {f"batch_{i}": f"value_{i}" for i in range(100)}
        await cache.batch_set(items)
        
        # Should use pipeline for efficiency
        redis_mock.pipeline.assert_called()
        assert pipeline_mock.set.call_count == 100
        pipeline_mock.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_get_operations(self):
        """Test batching multiple gets into single mget"""
        redis_mock = Mock()
        redis_mock.mget = Mock(return_value=[b"value1", b"value2", b"value3"])
        
        cache = HybridCache(redis_client=redis_mock)
        
        # Batch get operation
        keys = ["key1", "key2", "key3"]
        results = await cache.batch_get(keys)
        
        # Should use mget for efficiency
        redis_mock.mget.assert_called_once_with(keys)
        assert len(results) == 3