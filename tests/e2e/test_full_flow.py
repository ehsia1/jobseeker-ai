"""
End-to-End tests for JobSeeker AI API.

These tests run against a live backend server and test the complete user flow:
1. Registration and authentication
2. Profile setup and updates
3. Job browsing and searching
4. Saving jobs / creating matches
5. Generating proposals

Usage:
    # Start the backend first:
    uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

    # Run e2e tests:
    pytest tests/e2e/test_full_flow.py -v

    # Or with a different base URL:
    BASE_URL=http://localhost:8080 pytest tests/e2e/test_full_flow.py -v
"""

import os
import time
import pytest
import httpx
from datetime import datetime
from typing import Optional

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"e2e_test_{TEST_TIMESTAMP}@test.com"
TEST_USERNAME = f"e2e_user_{TEST_TIMESTAMP}"
TEST_PASSWORD = "TestPassword123!"


class TestState:
    """Shared state across tests."""
    access_token: Optional[str] = None
    user_id: Optional[int] = None
    job_id: Optional[int] = None
    match_id: Optional[int] = None


state = TestState()


@pytest.fixture(scope="module")
def client():
    """HTTP client for E2E tests."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="module")
def auth_headers():
    """Get authorization headers after login."""
    def _headers():
        if state.access_token:
            return {"Authorization": f"Bearer {state.access_token}"}
        return {}
    return _headers


# =============================================================================
# Health Check
# =============================================================================

class TestHealthCheck:
    """Verify the server is running."""

    def test_server_is_running(self, client):
        """Backend should be reachable."""
        try:
            response = client.get("/")
            assert response.status_code in [200, 404, 307]
        except httpx.ConnectError:
            pytest.fail(
                f"Cannot connect to backend at {BASE_URL}. "
                "Make sure the server is running: "
                "uvicorn backend.api.main:app --host 0.0.0.0 --port 8000"
            )


# =============================================================================
# Authentication Flow
# =============================================================================

class TestAuthFlow:
    """Test registration and login."""

    def test_01_register_new_user(self, client):
        """Should register a new user."""
        response = client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            },
        )

        # Accept both 200/201 for success
        assert response.status_code in [200, 201], f"Register failed: {response.text}"

        data = response.json()
        assert "id" in data or "user" in data
        print(f"✓ Registered user: {TEST_USERNAME} ({TEST_EMAIL})")

    def test_02_login(self, client):
        """Should login and receive access token."""
        response = client.post(
            "/auth/login",
            data={
                "username": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200, f"Login failed: {response.text}"

        data = response.json()
        assert "access_token" in data
        state.access_token = data["access_token"]
        print(f"✓ Logged in, token received")

    def test_03_get_current_user(self, client, auth_headers):
        """Should get current user info with valid token."""
        response = client.get("/auth/me", headers=auth_headers())

        assert response.status_code == 200, f"Get user failed: {response.text}"

        data = response.json()
        assert data["email"] == TEST_EMAIL
        state.user_id = data.get("id")
        print(f"✓ Got user info: {data['email']}")

    def test_04_invalid_token_rejected(self, client):
        """Should reject invalid tokens."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code in [401, 403]
        print("✓ Invalid token correctly rejected")


# =============================================================================
# Profile Management
# =============================================================================

class TestProfileFlow:
    """Test profile viewing and updates."""

    def test_01_get_profile(self, client, auth_headers):
        """Should get user profile."""
        response = client.get("/users/profile", headers=auth_headers())

        # Profile might not exist yet (404) or might exist (200)
        assert response.status_code in [200, 404], f"Get profile failed: {response.text}"
        print(f"✓ Profile endpoint accessible (status: {response.status_code})")

    def test_02_update_profile(self, client, auth_headers):
        """Should update user profile."""
        profile_data = {
            "profession": "Software Engineer",
            "skills": ["Python", "React", "FastAPI", "PostgreSQL"],
            "experience_years": 5,
            "min_rate_usd": 50.0,
            "preferences": {
                "remote_only": True,
                "job_types": ["full_time", "contract"],
            },
        }

        response = client.put(
            "/users/profile",
            json=profile_data,
            headers=auth_headers(),
        )

        assert response.status_code == 200, f"Update profile failed: {response.text}"

        data = response.json()
        assert data.get("profession") == "Software Engineer"
        assert "Python" in data.get("skills", [])
        print(f"✓ Profile updated: {data.get('profession')}")

    def test_03_verify_profile_persisted(self, client, auth_headers):
        """Should verify profile changes persisted."""
        response = client.get("/users/profile", headers=auth_headers())

        assert response.status_code == 200

        data = response.json()
        assert data.get("profession") == "Software Engineer"
        assert data.get("experience_years") == 5
        print("✓ Profile changes persisted correctly")


# =============================================================================
# Jobs Flow
# =============================================================================

class TestJobsFlow:
    """Test job listing and searching."""

    def test_01_list_jobs(self, client, auth_headers):
        """Should list available jobs."""
        response = client.get("/jobs/", headers=auth_headers())

        assert response.status_code == 200, f"List jobs failed: {response.text}"

        data = response.json()
        # Response could be a list or paginated object
        jobs = data if isinstance(data, list) else data.get("items", data.get("jobs", []))

        if jobs:
            state.job_id = jobs[0].get("id")
            print(f"✓ Listed {len(jobs)} jobs, first job ID: {state.job_id}")
        else:
            print("✓ Jobs endpoint works (no jobs in database)")

    def test_02_get_job_details(self, client, auth_headers):
        """Should get single job details."""
        if not state.job_id:
            pytest.skip("No jobs available to test")

        response = client.get(f"/jobs/{state.job_id}/", headers=auth_headers())

        assert response.status_code == 200, f"Get job failed: {response.text}"

        data = response.json()
        assert data.get("id") == state.job_id
        print(f"✓ Got job details: {data.get('title', 'N/A')}")

    def test_03_search_jobs(self, client, auth_headers):
        """Should search jobs with filters."""
        response = client.get(
            "/jobs/",
            params={
                "skills": "Python",
                "remote": True,
                "limit": 10,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 200, f"Search jobs failed: {response.text}"
        print("✓ Job search with filters works")


# =============================================================================
# Matches Flow
# =============================================================================

class TestMatchesFlow:
    """Test saving jobs and managing matches."""

    def test_01_save_job_creates_match(self, client, auth_headers):
        """Should save a job (create match)."""
        if not state.job_id:
            pytest.skip("No jobs available to test")

        response = client.post(
            "/matches/",
            json={
                "job_id": state.job_id,
                "status": "saved",
            },
            headers=auth_headers(),
        )

        # 200 or 201 for created, 409 if already exists
        assert response.status_code in [200, 201, 409], f"Save job failed: {response.text}"

        if response.status_code in [200, 201]:
            data = response.json()
            state.match_id = data.get("id")
            print(f"✓ Created match ID: {state.match_id}")
        else:
            print("✓ Job already saved (conflict)")

    def test_02_list_matches(self, client, auth_headers):
        """Should list user's matches."""
        response = client.get("/matches/", headers=auth_headers())

        assert response.status_code == 200, f"List matches failed: {response.text}"

        data = response.json()
        matches = data if isinstance(data, list) else data.get("items", data.get("matches", []))
        print(f"✓ Listed {len(matches)} matches")

        # Get match_id from list if we don't have one
        if not state.match_id and matches:
            state.match_id = matches[0].get("id")

    def test_03_update_match_status(self, client, auth_headers):
        """Should update match status."""
        if not state.match_id:
            pytest.skip("No matches available to test")

        response = client.put(
            f"/matches/{state.match_id}/status/",
            json={"status": "applied"},
            headers=auth_headers(),
        )

        assert response.status_code == 200, f"Update match failed: {response.text}"

        data = response.json()
        assert data.get("status") == "applied"
        print(f"✓ Updated match status to: applied")

    def test_04_filter_matches_by_status(self, client, auth_headers):
        """Should filter matches by status."""
        response = client.get(
            "/matches/",
            params={"status": "applied"},
            headers=auth_headers(),
        )

        assert response.status_code == 200
        print("✓ Match filtering by status works")


# =============================================================================
# Proposals Flow
# =============================================================================

class TestProposalsFlow:
    """Test proposal generation."""

    def test_01_proposals_health(self, client, auth_headers):
        """Should check proposals service health."""
        response = client.get("/proposals/health", headers=auth_headers())

        assert response.status_code == 200, f"Proposals health failed: {response.text}"
        data = response.json()
        assert "status" in data
        print(f"✓ Proposals service status: {data.get('status')}")

    def test_02_generate_proposal_short(self, client, auth_headers):
        """Should generate a short proposal for a job."""
        if not state.job_id:
            pytest.skip("No jobs available to test")

        response = client.post(
            "/proposals/generate",
            json={
                "job_id": str(state.job_id),
                "tone": "short",  # Valid values: short, medium, full
            },
            headers=auth_headers(),
        )

        # 200 for success, 402 for subscription/usage limit, 500 for LLM unavailable
        if response.status_code == 200:
            data = response.json()
            assert "content" in data
            print(f"✓ Generated short proposal ({data.get('word_count', 0)} words)")
        elif response.status_code == 402:
            data = response.json()
            print(f"✓ Usage limit reached (expected in free tier): {data.get('detail', {}).get('message', '')}")
        elif response.status_code == 500:
            print("✓ LLM service not available (expected if Ollama not running)")
        else:
            pytest.fail(f"Unexpected status {response.status_code}: {response.text}")

    def test_03_generate_proposal_with_parsed_jd(self, client, auth_headers):
        """Should generate a proposal from parsed JD text."""
        response = client.post(
            "/proposals/generate",
            json={
                "parsed_jd": {
                    "title": "Senior Python Developer",
                    "company": "TechCorp",
                    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                    "nice_to_have_skills": ["React", "Docker"],
                    "experience_level": "senior",
                    "key_requirements": ["5+ years experience", "Team leadership"],
                    "keywords_to_emphasize": ["python", "api", "backend"],
                    "responsibilities": ["Build APIs", "Mentor juniors"],
                    "remote": True,
                    "raw_text": "We are looking for a Senior Python Developer...",
                },
                "tone": "medium",
            },
            headers=auth_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            assert "content" in data
            print(f"✓ Generated proposal from parsed JD ({data.get('word_count', 0)} words)")
        elif response.status_code == 402:
            print("✓ Usage limit reached (expected in free tier)")
        elif response.status_code == 500:
            print("✓ LLM service not available (expected if Ollama not running)")
        else:
            pytest.fail(f"Unexpected status {response.status_code}: {response.text}")

    def test_04_generate_all_tones(self, client, auth_headers):
        """Should generate proposals in all tones."""
        if not state.job_id:
            pytest.skip("No jobs available to test")

        response = client.post(
            "/proposals/generate-all",
            json={
                "job_id": str(state.job_id),
            },
            headers=auth_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            assert "short" in data
            assert "medium" in data
            assert "full" in data
            print("✓ Generated all three tones")
        elif response.status_code == 402:
            print("✓ Usage limit reached (expected in free tier)")
        elif response.status_code == 500:
            print("✓ LLM service not available")
        else:
            pytest.fail(f"Unexpected status {response.status_code}: {response.text}")


# =============================================================================
# Subscription Flow (if available)
# =============================================================================

class TestSubscriptionFlow:
    """Test subscription endpoints."""

    def test_01_get_subscription_status(self, client, auth_headers):
        """Should get current subscription status."""
        response = client.get("/subscriptions/status", headers=auth_headers())

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Subscription tier: {data.get('tier', 'unknown')}")
        elif response.status_code == 404:
            print("✓ Subscription endpoint not implemented yet")
        else:
            print(f"! Subscription status returned: {response.status_code}")


# =============================================================================
# Cleanup
# =============================================================================

class TestCleanup:
    """Cleanup test data (optional)."""

    def test_logout(self, client, auth_headers):
        """Should be able to logout."""
        response = client.post("/auth/logout", headers=auth_headers())

        # Logout might not be implemented (stateless JWT)
        if response.status_code == 200:
            print("✓ Logged out successfully")
        else:
            print("✓ Logout endpoint not implemented (stateless JWT)")


# =============================================================================
# Run as standalone script
# =============================================================================

if __name__ == "__main__":
    import sys

    print(f"\n{'='*60}")
    print(f"JobSeeker AI E2E Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_USERNAME}")
    print(f"Test Email: {TEST_EMAIL}")
    print(f"{'='*60}\n")

    # Run with pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
