#!/bin/bash
# Run E2E tests against a live backend server
#
# Usage:
#   ./scripts/run_e2e_tests.sh              # Uses default localhost:8000
#   ./scripts/run_e2e_tests.sh 8080         # Uses localhost:8080
#   BASE_URL=http://prod.api.com ./scripts/run_e2e_tests.sh

set -e

PORT=${1:-8000}
BASE_URL=${BASE_URL:-"http://localhost:$PORT"}

echo "=================================="
echo "JobSeeker AI E2E Tests"
echo "=================================="
echo "Base URL: $BASE_URL"
echo ""

# Check if server is running
echo "Checking if server is running..."
if ! curl -s --max-time 5 "$BASE_URL" > /dev/null 2>&1; then
    echo "❌ Server not responding at $BASE_URL"
    echo ""
    echo "Start the server first:"
    echo "  source venv/bin/activate"
    echo "  uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT"
    exit 1
fi

echo "✓ Server is running"
echo ""

# Run tests
cd "$(dirname "$0")/.."
source venv/bin/activate

echo "Running E2E tests..."
echo ""

BASE_URL=$BASE_URL pytest tests/e2e/test_full_flow.py -v --tb=short "$@"

echo ""
echo "=================================="
echo "E2E Tests Complete"
echo "=================================="
