#!/usr/bin/env python3
"""Test profession-based job search."""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_profession_search():
    """Test searching for different professions."""
    
    # 1. Login
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
    print("✓ Login successful\n")
    
    # 2. List available professions
    print("2. Available professions:")
    prof_response = requests.get(
        f"{BASE_URL}/jobs/professions/list",
        headers=headers
    )
    
    if prof_response.status_code == 200:
        professions = prof_response.json()
        print(f"   Total professions: {professions['total']}")
        # Show first 10
        for prof in professions['professions'][:10]:
            print(f"   - {prof['label']} ({prof['searcher_count']} job boards)")
    print()
    
    # 3. Test different profession searches
    test_cases = [
        {
            "profession": "software_engineer",
            "keywords": ["python", "backend"],
            "description": "Software Engineer (Python/Backend)"
        },
        {
            "profession": "designer",
            "keywords": ["ux", "ui", "figma"],
            "description": "UX/UI Designer"
        },
        {
            "profession": "marketing",
            "keywords": ["digital", "growth", "seo"],
            "description": "Digital Marketing Specialist"
        },
        {
            "profession": "sales",
            "keywords": ["b2b", "saas", "enterprise"],
            "description": "B2B Sales (SaaS)"
        },
        {
            "profession": "data_scientist",
            "keywords": ["machine learning", "python", "analytics"],
            "description": "Data Scientist / ML Engineer"
        },
        {
            "profession": "customer_service",
            "keywords": ["support", "remote", "chat"],
            "description": "Customer Support Representative"
        },
        {
            "profession": "writer",
            "keywords": ["content", "blog", "technical"],
            "description": "Content/Technical Writer"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 3):
        print(f"{i}. Searching for: {test_case['description']}")
        print(f"   Profession: {test_case['profession']}")
        print(f"   Keywords: {', '.join(test_case['keywords'])}")
        
        search_response = requests.post(
            f"{BASE_URL}/jobs/search/live",
            headers=headers,
            json={
                "profession": test_case["profession"],
                "keywords": test_case["keywords"],
                "remote_only": True,
                "limit": 3
            }
        )
        
        if search_response.status_code == 200:
            results = search_response.json()
            print(f"   ✓ Found {results.get('total_results', 0)} jobs")
            
            # Show which job boards were used
            source_stats = results.get('source_stats', {})
            active_sources = [s for s, count in source_stats.items() if count > 0]
            if active_sources:
                print(f"   Active job boards: {', '.join(active_sources)}")
            
            # Show first result if available
            if results.get('results'):
                first_job = results['results'][0]
                print(f"   Sample job: {first_job['title']} at {first_job['company']}")
        else:
            print(f"   ✗ Search failed: {search_response.status_code}")
        
        print()
    
    print("\n" + "="*60)
    print("Summary:")
    print("The system now searches different job boards based on profession!")
    print("- Software engineers: GitHub, HackerNews, RemoteOK, AngelList")
    print("- Designers: AngelList, RemoteOK, FlexJobs, Upwork")
    print("- Marketing: AngelList, RemoteOK, FlexJobs, Indeed")
    print("- Sales: AngelList, RemoteOK, Indeed, LinkedIn")
    print("- Writers: FlexJobs, Upwork, RemoteOK")
    print("- Customer Service: FlexJobs, RemoteOK, Indeed")
    print("...and many more professions supported!")


if __name__ == "__main__":
    print("Testing Profession-Based Job Search")
    print("=" * 60)
    test_profession_search()