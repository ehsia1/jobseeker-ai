#!/usr/bin/env python3
"""
Test script to verify frontend can connect to backend
Run the backend first: python backend/api/main.py
Then open frontend: http://localhost:3000/search
"""

import requests
import json

def test_backend_health():
    """Test if backend is running"""
    try:
        response = requests.get("http://localhost:8080/health")
        if response.status_code == 200:
            print("✅ Backend health check passed")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not running: {e}")
        return False

def test_job_search():
    """Test job search endpoint"""
    try:
        search_data = {
            "keywords": ["python", "developer"],
            "remote_only": True,
            "limit": 5
        }
        
        response = requests.post(
            "http://localhost:8080/jobs/search",
            json=search_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Job search successful")
            print(f"   - Total results: {data.get('total_results', 0)}")
            print(f"   - Sources: {', '.join(data.get('source_stats', {}).keys())}")
            return True
        else:
            print(f"❌ Job search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Job search error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing JobSeeker AI Backend...")
    print("-" * 40)
    
    if test_backend_health():
        print("\n📋 Testing Job Search API...")
        test_job_search()
    else:
        print("\n⚠️  Please start the backend first:")
        print("   cd /Users/evan/code/jobseeker-ai")
        print("   python backend/api/main.py")
    
    print("\n🌐 Frontend Instructions:")
    print("-" * 40)
    print("1. Frontend is running at: http://localhost:3000")
    print("2. Navigate to: http://localhost:3000/search")
    print("3. Try searching for 'python developer' or 'react'")
    print("4. Select a profession filter like 'Software Engineer'")
    print("5. Toggle remote-only option")
    print("\n✨ The search will query multiple job boards in real-time!")