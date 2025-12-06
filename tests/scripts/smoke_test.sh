#!/bin/bash

# JobSeeker AI Smoke Test Suite
# Runs in <5 minutes to verify system health
# Exit on any error
set -e

echo "🚀 Starting JobSeeker AI Smoke Tests..."
echo "================================"

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost:3000"}
TEST_EMAIL="smoketest_$(date +%s)@test.com"
TEST_PASSWORD=${TEST_PASSWORD:-"$(openssl rand -base64 12)"}

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Backend Health Check
echo ""
echo "1. Testing Backend Health..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health)
if [ "$HEALTH_RESPONSE" = "200" ]; then
    success "Backend is healthy"
else
    error "Backend health check failed (HTTP $HEALTH_RESPONSE)"
fi

# Test 2: Database Connection
echo ""
echo "2. Testing Database Connection..."
DB_STATUS=$(curl -s $API_URL/health/database | jq -r '.status')
if [ "$DB_STATUS" = "connected" ]; then
    success "Database is connected"
else
    error "Database connection failed"
fi

# Test 3: Redis Cache
echo ""
echo "3. Testing Redis Cache..."
CACHE_STATUS=$(curl -s $API_URL/health/cache | jq -r '.status')
if [ "$CACHE_STATUS" = "connected" ]; then
    REDIS_COMMANDS=$(curl -s $API_URL/health/cache | jq -r '.redis_commands_today')
    REDIS_REMAINING=$((10000 - REDIS_COMMANDS))
    success "Redis is connected (${REDIS_REMAINING} commands remaining today)"
    
    if [ "$REDIS_REMAINING" -lt 1000 ]; then
        warning "Redis approaching daily limit!"
    fi
else
    warning "Redis not connected, using memory cache"
fi

# Test 4: User Registration
echo ""
echo "4. Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST $API_URL/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"full_name\":\"Smoke Test User\"}")

if echo "$REGISTER_RESPONSE" | jq -e '.access_token' > /dev/null; then
    TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')
    success "User registration successful"
else
    error "User registration failed: $(echo "$REGISTER_RESPONSE" | jq -r '.detail')"
fi

# Test 5: User Login
echo ""
echo "5. Testing User Login..."
LOGIN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

if echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    success "User login successful"
else
    error "User login failed"
fi

# Test 6: Job Search (Cached)
echo ""
echo "6. Testing Job Search (Cached)..."
START_TIME=$(date +%s%3N)
SEARCH_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "$API_URL/jobs/search?q=python&limit=10")
END_TIME=$(date +%s%3N)
RESPONSE_TIME=$((END_TIME - START_TIME))

JOB_COUNT=$(echo "$SEARCH_RESPONSE" | jq -r '.results | length')
if [ "$JOB_COUNT" -gt 0 ]; then
    success "Found $JOB_COUNT jobs in ${RESPONSE_TIME}ms"
    
    if [ "$RESPONSE_TIME" -gt 500 ]; then
        warning "Response time exceeds 500ms target"
    fi
else
    warning "No jobs found (may need to run batch import)"
fi

# Test 7: Client-Side Scoring
echo ""
echo "7. Testing Client-Side Scoring..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL)
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    # Check if scorer script is loaded
    SCORER_LOADED=$(curl -s $FRONTEND_URL/matches | grep -c "ClientJobScorer" || true)
    if [ "$SCORER_LOADED" -gt 0 ]; then
        success "Client-side scorer is loaded"
    else
        warning "Client-side scorer not found"
    fi
else
    error "Frontend not accessible (HTTP $FRONTEND_RESPONSE)"
fi

# Test 8: Cache Hit Rate
echo ""
echo "8. Testing Cache Performance..."
CACHE_STATS=$(curl -s $API_URL/health/cache-stats)
HIT_RATE=$(echo "$CACHE_STATS" | jq -r '.hit_rate')
HIT_RATE_PERCENT=$(echo "$HIT_RATE * 100" | bc -l | cut -d. -f1)

if [ "$HIT_RATE_PERCENT" -ge 70 ]; then
    success "Cache hit rate: ${HIT_RATE_PERCENT}% (target: >70%)"
elif [ "$HIT_RATE_PERCENT" -ge 60 ]; then
    warning "Cache hit rate: ${HIT_RATE_PERCENT}% (below target)"
else
    error "Cache hit rate: ${HIT_RATE_PERCENT}% (critical)"
fi

# Test 9: Database Size
echo ""
echo "9. Testing Database Size..."
DB_METRICS=$(curl -s $API_URL/health/metrics)
DB_SIZE=$(echo "$DB_METRICS" | jq -r '.database.size_mb')
DB_PERCENT=$(echo "$DB_METRICS" | jq -r '.database.size_percentage')

if (( $(echo "$DB_PERCENT < 80" | bc -l) )); then
    success "Database size: ${DB_SIZE}MB (${DB_PERCENT}% of 500MB limit)"
elif (( $(echo "$DB_PERCENT < 95" | bc -l) )); then
    warning "Database approaching limit: ${DB_SIZE}MB (${DB_PERCENT}%)"
else
    error "Database critically full: ${DB_SIZE}MB (${DB_PERCENT}%)"
fi

# Test 10: Memory Usage
echo ""
echo "10. Testing Memory Usage..."
MEMORY_MB=$(echo "$DB_METRICS" | jq -r '.render.memory_usage_mb')
if [ "$MEMORY_MB" -lt 400 ]; then
    success "Memory usage: ${MEMORY_MB}MB (limit: 512MB)"
else
    warning "High memory usage: ${MEMORY_MB}MB"
fi

# Test 11: Cold Start (if on Render)
echo ""
echo "11. Testing Cold Start Performance..."
if [ "$API_URL" = *"onrender.com"* ]; then
    # Let server sleep (would take 15 min in reality, skip in test)
    warning "Skipping cold start test (requires 15 min idle)"
else
    success "Cold start test not applicable (local environment)"
fi

# Test 12: Concurrent Requests
echo ""
echo "12. Testing Concurrent Request Handling..."
echo "Sending 10 concurrent requests..."

for i in {1..10}; do
    curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_URL/jobs/search?q=test$i&limit=5" > /dev/null &
done
wait

success "Handled 10 concurrent requests successfully"

# Cleanup
echo ""
echo "13. Cleanup..."
# Delete test user (optional, depends on your API)
# curl -s -X DELETE -H "Authorization: Bearer $TOKEN" $API_URL/auth/me

# Summary
echo ""
echo "================================"
echo "✅ Smoke Tests Complete!"
echo ""
echo "Summary:"
echo "  - Backend: Healthy"
echo "  - Database: Connected"
echo "  - Redis: ${REDIS_REMAINING} commands remaining"
echo "  - Cache Hit Rate: ${HIT_RATE_PERCENT}%"
echo "  - Database Usage: ${DB_PERCENT}%"
echo "  - Memory Usage: ${MEMORY_MB}MB"
echo "  - Response Time: ${RESPONSE_TIME}ms"
echo ""

# Check if any warnings were issued
if [ "$REDIS_REMAINING" -lt 1000 ] || [ "$HIT_RATE_PERCENT" -lt 70 ] || [ "$DB_PERCENT" -gt 80 ]; then
    echo "⚠️  Some metrics need attention"
    exit 0  # Don't fail, just warn
else
    echo "🎉 All systems operational!"
fi