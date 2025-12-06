# JobSeeker AI Testing Suite

This directory contains all tests for the JobSeeker AI platform, specifically designed to validate our zero-cost architecture.

## Test Structure

```
tests/
├── backend/
│   ├── unit/              # Fast, isolated unit tests
│   ├── integration/       # API and database integration tests
│   └── chaos/            # Chaos tests for free-tier limits
├── frontend/
│   ├── components/       # React component tests
│   └── e2e/             # End-to-end browser tests
└── scripts/
    └── smoke_test.sh    # 5-minute production smoke test
```

## Running Tests

### Quick Commands

```bash
# Run all tests
make test

# Run specific test suites
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-chaos        # Chaos tests for free tier limits
make test-smoke        # Smoke tests (5 minutes)

# Test specific limits
make test-redis-limits  # Test Redis 10K command limit
make test-db-limits    # Test Supabase 500MB limit

# Coverage report
make test-coverage     # Generate coverage report (target: 70%)
```

### Python Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all backend tests
pytest tests/backend/

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific markers
pytest -m unit        # Unit tests only
pytest -m chaos       # Chaos tests only
pytest -m smoke       # Smoke tests only
```

### Frontend Tests

```bash
# Install dependencies
cd frontend/web && npm install

# Run tests
npm test              # Unit tests
npm run test:e2e      # E2E tests
npm run test:coverage # With coverage
```

## Test Categories

### 1. Unit Tests (`tests/backend/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (<100ms per test)
- **Dependencies**: None (all mocked)
- **Coverage Target**: 80%

### 2. Integration Tests (`tests/backend/integration/`)
- **Purpose**: Test API endpoints and database operations
- **Speed**: Medium (100ms-1s per test)
- **Dependencies**: PostgreSQL, Redis
- **Coverage Target**: 70%

### 3. Chaos Tests (`tests/backend/chaos/`)
- **Purpose**: Test behavior at free-tier limits
- **Tests**:
  - Redis 10K daily command limit
  - Supabase 500MB storage limit
  - Render auto-sleep after 15 minutes
  - Client-side scoring accuracy
- **Speed**: Slow (>1s per test)
- **Critical**: Must pass before production

### 4. Smoke Tests (`tests/scripts/smoke_test.sh`)
- **Purpose**: Quick health check of production system
- **Duration**: <5 minutes
- **Checks**:
  - API health
  - Database connection
  - Redis availability
  - Authentication flow
  - Job search performance
  - Cache hit rate
  - Free tier usage

## Free Tier Testing Focus

Our tests specifically validate behavior when approaching free tier limits:

### Redis (Upstash) - 10K commands/day
```python
# Test at 95% capacity (9,500 commands)
- System switches to memory cache
- No user-facing errors
- Monitoring alerts triggered

# Test at 100% capacity (10,000 commands)
- Graceful fallback to memory
- Service remains available
- Auto-recovery at midnight UTC
```

### Database (Supabase) - 500MB
```python
# Test at 80% capacity (400MB)
- Auto-cleanup of old jobs (>30 days)
- Alert notifications sent
- New imports paused

# Test at 95% capacity (475MB)
- Emergency cleanup (>7 days)
- Read-only mode for non-critical features
- User registration paused
```

### Render - Auto-sleep
```python
# Test cold start performance
- Time to first byte: <3s
- Full response: <5s
- Connection pool recovery: <2s
```

## CI/CD Integration

Tests run automatically via GitHub Actions:

- **On Push**: Unit + Integration tests
- **On PR**: Full test suite
- **Scheduled**: Chaos tests every 6 hours
- **Pre-deploy**: Smoke tests

## Writing New Tests

### Test Template

```python
"""Test module description"""
import pytest
from unittest.mock import Mock

class TestFeatureName:
    """Test class description"""
    
    @pytest.fixture
    def setup(self):
        """Setup test fixtures"""
        return Mock()
    
    @pytest.mark.unit  # or integration, chaos, smoke
    async def test_specific_behavior(self, setup):
        """Test description"""
        # Arrange
        expected = "value"
        
        # Act
        result = function_under_test()
        
        # Assert
        assert result == expected
```

### Testing Best Practices

1. **Keep tests fast**: Unit tests should run in <100ms
2. **Test one thing**: Each test should verify a single behavior
3. **Use descriptive names**: `test_cache_falls_back_to_memory_when_redis_unavailable`
4. **Mock external dependencies**: Don't hit real APIs in unit tests
5. **Test edge cases**: Especially free-tier limits
6. **Clean up**: Ensure tests don't leave artifacts

## Monitoring Test Results

```bash
# View HTML coverage report
open htmlcov/index.html

# Check test metrics
make monitor-all

# View Redis usage
make monitor-redis

# Check database size
make monitor-db
```

## Troubleshooting

### Common Issues

1. **Redis connection failed**
   ```bash
   docker-compose up -d redis
   ```

2. **Database not found**
   ```bash
   docker-compose up -d postgres
   make migrate
   ```

3. **Slow tests**
   - Check for missing mocks
   - Use `pytest-timeout` to identify hanging tests
   - Run tests in parallel: `pytest -n auto`

4. **Flaky tests**
   - Add retries for network operations
   - Use fixed timestamps with `freezegun`
   - Ensure proper test isolation

## Coverage Goals

- **Overall**: 70% minimum
- **Critical paths**: 90% (auth, payment, scoring)
- **Chaos scenarios**: 100% (all limits tested)
- **Smoke tests**: Must pass 100%

## Contact

For questions about testing:
- Check `TESTING_PLAN.md` for detailed strategy
- Review `.github/workflows/ci.yml` for CI configuration
- Run `make help` for available commands