#!/usr/bin/env python3
"""Test job search via API endpoints."""

import requests
import json
from pprint import pprint

# API base URL
BASE_URL = "http://localhost:8080"

def test_job_search_api():
    """Test job search through the API."""
    
    # First, login to get a token
    print("1. Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "testuser", "password": "testpass123"}
    )
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Login successful")
    
    # 2. Search for jobs by keywords (live from job boards)
    print("\n2. Searching for jobs by keywords (live from job boards)...")
    search_response = requests.post(
        f"{BASE_URL}/jobs/search/live",
        headers=headers,
        json={
            "keywords": ["python", "backend", "remote"],
            "remote_only": True,
            "limit": 5
        }
    )
    
    if search_response.status_code == 200:
        results = search_response.json()
        print(f"✓ Found {results.get('total_results', 0)} jobs")
        print(f"  Source breakdown: {results.get('source_stats', {})}")
        
        # Show first 3 results
        if results.get('results'):
            print("\n  Sample results:")
            for i, job in enumerate(results['results'][:3], 1):
                print(f"\n  Job {i}:")
                print(f"    Source: {job['source']}")
                print(f"    Title: {job['title']}")
                print(f"    Company: {job['company']}")
                print(f"    Remote: {job['remote']}")
                if job.get('skills'):
                    print(f"    Skills: {', '.join(job['skills'][:5])}")
    else:
        print(f"✗ Search failed: {search_response.status_code}")
        print(f"  Error: {search_response.text}")
    
    # 3. Search jobs for user profile
    print("\n3. Searching jobs based on user profile...")
    profile_search = requests.post(
        f"{BASE_URL}/jobs/search/profile",
        headers=headers,
        json={}
    )
    
    if profile_search.status_code == 200:
        results = profile_search.json()
        print(f"✓ Found {results.get('total_results', 0)} jobs matching profile")
        print(f"  New jobs stored: {results.get('stored_jobs', 0)}")
        print(f"  Source breakdown: {results.get('source_stats', {})}")
    else:
        print(f"✗ Profile search failed: {profile_search.status_code}")
        print(f"  Error: {profile_search.text}")
    
    # 4. Get job matches
    print("\n4. Getting job matches...")
    matches_response = requests.get(
        f"{BASE_URL}/matches",
        headers=headers
    )
    
    if matches_response.status_code == 200:
        matches = matches_response.json()
        print(f"✓ Found {len(matches)} job matches")
        if matches:
            print("\n  Top matches:")
            for i, match in enumerate(matches[:3], 1):
                print(f"\n  Match {i}:")
                print(f"    Job: {match['job']['title']} at {match['job']['company']}")
                print(f"    Score: {match['score']:.2f}")
                print(f"    Status: {match['status']}")
    else:
        print(f"✗ Getting matches failed: {matches_response.status_code}")


if __name__ == "__main__":
    print("Testing Job Search API Endpoints")
    print("=" * 50)
    test_job_search_api()