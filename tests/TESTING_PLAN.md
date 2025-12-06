# JobSeeker AI Testing Plan - Zero-Cost Architecture

## Critical Testing Focus Areas

### 1. Free Tier Breaking Points

#### Redis (Upstash) - 10K Commands/Day Limit
```bash
# Test: Redis Command Exhaustion
npm run test:redis-limits

# What happens at 9,500 commands (95% threshold)?
- Switch to InMemoryCache automatically
- Log warning to monitoring
- Continue serving from memory

# What happens at 10,000 commands?
- Redis returns rate limit error
- System falls back to memory cache
- No user-facing errors

# Recovery test
- Reset at midnight UTC
- Verify Redis reconnection
- Cache sync validation
```

#### Supabase - 500MB Storage Limit
```bash
# Test: Database Size Monitoring
npm run test:db-size

# At 400MB (80% threshold):
- Trigger automatic cleanup of jobs > 30 days old
- Alert via webhook to Discord/Slack
- Pause batch job imports

# At 475MB (95% threshold):
- Emergency cleanup of jobs > 7 days old
- Disable new user registrations temporarily
- Switch to read-only mode for non-critical features
```

#### Render - Auto-Sleep After 15 Minutes
```bash
# Test: Cold Start Performance
npm run test:cold-start

# Measure:
- Time to first byte after sleep: Target < 3s
- Full API response after wake: Target < 5s
- Database connection pool recovery: Target < 2s

# Mitigation:
- Implement health check endpoint
- Use Uptime Robot to ping every 14 minutes
- Preload critical data on startup
```

### 2. Cache Strategy Testing

#### 6-Hour TTL Validation
```python
# backend/tests/test_cache_strategy.py
import pytest
from datetime import datetime, timedelta
from backend.services.cache_service import HybridCache

@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Verify 6-hour cache expiration works correctly"""
    cache = HybridCache()
    
    # Store with 6-hour TTL
    await cache.set("test_key", {"data": "test"}, ttl_hours=6)
    
    # Fast-forward time
    with freeze_time(datetime.now() + timedelta(hours=5, minutes=59)):
        result = await cache.get("test_key")
        assert result is not None  # Still cached
    
    with freeze_time(datetime.now() + timedelta(hours=6, minutes=1)):
        result = await cache.get("test_key")
        assert result is None  # Expired

@pytest.mark.asyncio
async def test_cache_fallback_chain():
    """Test Redis -> Memory -> Database fallback"""
    # Simulate Redis failure
    cache = HybridCache(redis_client=None)
    
    # Should use memory cache
    await cache.set("test_key", {"data": "test"})
    result = await cache.get("test_key")
    assert result["data"] == "test"
    assert cache.stats["memory_hits"] == 1
```

#### Batch Search System (30-minute intervals)
```python
@pytest.mark.asyncio
async def test_batch_search_timing():
    """Ensure batch searches run exactly every 30 minutes"""
    scheduler = BatchSearchScheduler()
    
    # Record execution times
    executions = []
    scheduler.on_execute = lambda: executions.append(datetime.now())
    
    # Run for 2 hours
    await scheduler.run_for_duration(hours=2)
    
    # Should have 4 executions
    assert len(executions) == 4
    
    # Check 30-minute intervals
    for i in range(1, len(executions)):
        delta = executions[i] - executions[i-1]
        assert 29 <= delta.total_seconds() / 60 <= 31
```

### 3. Client-Side Processing Tests

#### Job Scoring Accuracy
```typescript
// frontend/web/src/lib/scoring/__tests__/scorer.test.ts
import { ClientJobScorer } from '../client-scorer';
import { mockJob, mockProfile } from '../__fixtures__';

describe('Client-Side Scoring', () => {
  const scorer = new ClientJobScorer();
  
  test('matches server-side scoring within 5% margin', async () => {
    const clientScore = scorer.scoreJob(mockJob, mockProfile);
    
    // Call server for comparison
    const serverScore = await fetch('/api/jobs/score', {
      method: 'POST',
      body: JSON.stringify({ job: mockJob, profile: mockProfile })
    }).then(r => r.json());
    
    const difference = Math.abs(clientScore - serverScore.score);
    expect(difference).toBeLessThanOrEqual(5);
  });
  
  test('handles 1000 jobs without blocking UI', () => {
    const jobs = Array(1000).fill(mockJob);
    const startTime = performance.now();
    
    scorer.scoreAndRankJobs(jobs, mockProfile);
    
    const duration = performance.now() - startTime;
    expect(duration).toBeLessThan(100); // Should complete in <100ms
  });
});
```

### 4. Chaos Testing Scenarios

#### Scenario 1: Redis Exhaustion During Peak
```bash
#!/bin/bash
# tests/chaos/redis_exhaustion.sh

echo "Starting Redis exhaustion test..."

# 1. Generate 9000 cache operations
for i in {1..9000}; do
  curl -X GET "http://localhost:8000/api/jobs/search?q=test$i" &
done
wait

# 2. Monitor memory cache takeover
curl http://localhost:8000/api/health/cache-stats

# 3. Generate 2000 more operations (should use memory)
for i in {9001..11000}; do
  curl -X GET "http://localhost:8000/api/jobs/search?q=test$i" &
done
wait

# 4. Verify no errors returned to users
# Check logs for fallback messages
grep "Redis limit reached, using memory cache" logs/app.log
```

#### Scenario 2: Render Sleep/Wake Cycle
```bash
#!/bin/bash
# tests/chaos/render_sleep_test.sh

# 1. Let server go idle for 16 minutes
echo "Waiting for server to sleep..."
sleep 960

# 2. Send burst of 100 simultaneous requests
for i in {1..100}; do
  curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/jobs/search" &
done
wait

# 3. Analyze response times
# First request should be <5s, others <500ms
```

#### Scenario 3: Database Size Limit Approach
```python
# tests/chaos/db_size_test.py
import asyncio
from backend.tests.factories import JobFactory

async def fill_database_to_threshold():
    """Fill database to 90% capacity"""
    target_size_mb = 450  # 90% of 500MB
    
    while get_current_db_size() < target_size_mb:
        # Create 1000 jobs with large descriptions
        jobs = [JobFactory.create(
            description="x" * 10000  # 10KB per job
        ) for _ in range(1000)]
        
        await db.bulk_insert(jobs)
        
        # Check cleanup triggered
        if get_current_db_size() > 400:
            assert cleanup_service.is_running()
    
    # Verify system still functional
    response = await client.get("/api/jobs/search")
    assert response.status_code == 200
```

### 5. Smoke Test Suite (5-minute execution)

```yaml
# .github/workflows/smoke-tests.yml
name: Smoke Tests
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    
    steps:
      - name: Health Check
        run: |
          curl -f https://api.jobseeker.ai/health || exit 1
          
      - name: Auth Flow
        run: |
          # Register
          TOKEN=$(curl -X POST https://api.jobseeker.ai/auth/register \
            -d '{"email":"test@example.com","password":"test123"}' \
            | jq -r '.token')
          
          # Login
          curl -H "Authorization: Bearer $TOKEN" \
            https://api.jobseeker.ai/auth/me || exit 1
            
      - name: Search Jobs
        run: |
          # Test cached search (should be fast)
          time curl "https://api.jobseeker.ai/jobs/search?q=python" \
            | grep -q '"results"' || exit 1
            
      - name: Client-Side Scoring
        run: |
          # Load frontend and verify scorer loads
          curl https://jobseeker.ai/matches | grep -q 'ClientJobScorer' || exit 1
          
      - name: Cache Stats
        run: |
          STATS=$(curl https://api.jobseeker.ai/health/cache-stats)
          echo "Cache hit rate: $(echo $STATS | jq -r '.hit_rate')"
          
          # Alert if hit rate < 60%
          HIT_RATE=$(echo $STATS | jq -r '.hit_rate')
          if (( $(echo "$HIT_RATE < 0.6" | bc -l) )); then
            echo "WARNING: Low cache hit rate"
          fi
```

### 6. Production Monitoring (Zero-Cost)

#### Sentry Free Tier (5K events/month)
```python
# backend/monitoring.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.01,  # Only 1% of transactions
    profiles_sample_rate=0.01,
    before_send=lambda event, hint: filter_non_critical(event)
)

def filter_non_critical(event):
    """Only send critical errors to stay under 5K/month"""
    if event.get('level') in ['error', 'fatal']:
        return event
    return None  # Drop warnings and info
```

#### Custom Metrics Endpoint
```python
@router.get("/health/metrics")
async def get_metrics():
    """Lightweight metrics for monitoring"""
    return {
        "cache": {
            "redis_commands_today": await redis.get("daily_command_count"),
            "redis_remaining": 10000 - int(await redis.get("daily_command_count") or 0),
            "memory_cache_size": len(memory_cache.cache),
            "hit_rate": calculate_hit_rate()
        },
        "database": {
            "size_mb": get_db_size_mb(),
            "size_percentage": (get_db_size_mb() / 500) * 100,
            "total_jobs": await db.count(Job),
            "total_users": await db.count(User)
        },
        "render": {
            "uptime_seconds": time.time() - START_TIME,
            "last_sleep": last_sleep_time,
            "memory_usage_mb": get_process_memory_mb()
        },
        "errors_last_hour": error_counter.get_last_hour(),
        "alerts": check_alert_conditions()
    }
```

#### Uptime Monitoring (Free)
```yaml
# uptime-robot-config.yml
monitors:
  - name: API Health
    url: https://api.jobseeker.ai/health
    interval: 300  # 5 minutes
    
  - name: Keep Alive (Prevent Sleep)
    url: https://api.jobseeker.ai/ping
    interval: 840  # 14 minutes (before 15-minute sleep)
    
  - name: Frontend
    url: https://jobseeker.ai
    interval: 300
    
  - name: Cache Stats
    url: https://api.jobseeker.ai/health/cache-stats
    interval: 1800  # 30 minutes
    keyword: "hit_rate"  # Alert if missing
```

## Test Execution Strategy

### Daily Tests (Automated)
1. Smoke tests (5 min)
2. Cache hit rate check
3. Database size check
4. Redis command count

### Weekly Tests (Manual)
1. Redis exhaustion simulation
2. Cold start performance
3. Batch search validation
4. Client-side scoring accuracy

### Pre-Deployment Tests
1. Full test suite
2. Load test with free-tier limits
3. Chaos scenarios
4. Rollback procedure validation

## Success Criteria

✅ **Must Pass:**
- Zero user-facing errors when hitting free tier limits
- Cache hit rate > 70%
- Cold start < 5 seconds
- Client scoring matches server ±5%
- Automatic cleanup triggers at 80% database capacity

⚠️ **Should Pass:**
- Redis fallback seamless
- Batch searches on schedule ±1 minute
- Memory usage < 400MB on Render
- Response time < 500ms for cached requests

📊 **Metrics to Track:**
- Daily Redis command usage
- Database growth rate
- Cache hit/miss ratio
- Cold start frequency
- Error rate by type

## Rollback Plan

If deployment fails:
1. Revert to previous Docker image on Render
2. Restore database from Supabase backup
3. Clear Redis cache
4. Revert frontend on Vercel
5. Notify users of temporary disruption

## Next Steps

1. Implement test scripts in `/tests` directory
2. Set up GitHub Actions for automated testing
3. Configure Uptime Robot monitors
4. Create dashboard for metrics visualization
5. Document runbooks for common failures