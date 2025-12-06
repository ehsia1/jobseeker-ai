#!/usr/bin/env python3
"""Test the complete job matching flow."""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def test_matching_flow():
    """Test the complete matching flow."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}JobSeeker AI - Matching Flow Test{Colors.ENDC}")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Login
        print(f"\n{Colors.CYAN}Step 1: Authenticating...{Colors.ENDC}")
        login_data = {
            "username": "testuser",
            "password": "TestPassword123!"
        }
        
        async with session.post(
            f"{base_url}/auth/login",
            data=login_data
        ) as response:
            if response.status == 200:
                auth_data = await response.json()
                token = auth_data["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                print(f"{Colors.GREEN}✅ Authenticated successfully{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ Authentication failed{Colors.ENDC}")
                return
        
        # Step 2: Update user profile
        print(f"\n{Colors.CYAN}Step 2: Updating user profile...{Colors.ENDC}")
        profile_update = {
            "skills": ["Python", "FastAPI", "Machine Learning", "PostgreSQL", "Docker"],
            "experience_years": 5,
            "preferences": {
                "remote_only": True,
                "job_types": ["full-time", "contract"],
                "industries": ["tech", "ai", "startup"]
            },
            "min_rate_usd": 75.0,
            "max_hours_per_week": 40
        }
        
        async with session.put(
            f"{base_url}/users/profile",
            json=profile_update,
            headers=headers
        ) as response:
            if response.status == 200:
                print(f"{Colors.GREEN}✅ Profile updated{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}⚠️  Profile update failed{Colors.ENDC}")
        
        # Step 3: Create sample jobs
        print(f"\n{Colors.CYAN}Step 3: Creating sample jobs...{Colors.ENDC}")
        sample_jobs = [
            {
                "source": "test",
                "source_id": "test-001",
                "title": "Senior Python Developer - AI/ML Focus",
                "company": "TechCorp AI",
                "description": "We're looking for a senior Python developer with strong ML experience to join our team. You'll work on cutting-edge AI projects using FastAPI and modern ML frameworks.",
                "requirements": ["5+ years Python", "ML experience", "FastAPI knowledge"],
                "skills": ["Python", "Machine Learning", "FastAPI", "Docker", "PostgreSQL"],
                "rate_min": 80,
                "rate_max": 120,
                "rate_type": "hourly",
                "location": "Remote",
                "remote": True,
                "hours_per_week": 40,
                "duration": "6 months",
                "posted_at": datetime.utcnow().isoformat(),
                "url": "https://example.com/job1"
            },
            {
                "source": "test",
                "source_id": "test-002",
                "title": "Full Stack Developer - React & Node",
                "company": "StartupXYZ",
                "description": "Fast-growing startup needs a full stack developer proficient in React and Node.js. Remote position with flexible hours.",
                "requirements": ["React expertise", "Node.js", "3+ years experience"],
                "skills": ["React", "Node.js", "JavaScript", "MongoDB"],
                "rate_min": 60,
                "rate_max": 90,
                "rate_type": "hourly",
                "location": "Remote",
                "remote": True,
                "hours_per_week": 30,
                "duration": "3 months",
                "posted_at": datetime.utcnow().isoformat(),
                "url": "https://example.com/job2"
            },
            {
                "source": "test",
                "source_id": "test-003",
                "title": "Data Engineer - PostgreSQL Expert",
                "company": "DataCo",
                "description": "Looking for a data engineer with deep PostgreSQL knowledge and Python skills. Work on large-scale data pipelines.",
                "requirements": ["PostgreSQL expert", "Python", "Data pipelines"],
                "skills": ["PostgreSQL", "Python", "Apache Airflow", "Docker"],
                "rate_min": 75,
                "rate_max": 100,
                "rate_type": "hourly",
                "location": "Remote",
                "remote": True,
                "hours_per_week": 40,
                "duration": "Long-term",
                "posted_at": datetime.utcnow().isoformat(),
                "url": "https://example.com/job3"
            }
        ]
        
        jobs_created = []
        for job in sample_jobs:
            async with session.post(
                f"{base_url}/jobs/",
                json=job,
                headers=headers
            ) as response:
                if response.status == 200:
                    job_data = await response.json()
                    jobs_created.append(job_data)
                    print(f"  ✅ Created: {job['title'][:50]}")
                else:
                    print(f"  ❌ Failed: {job['title'][:50]}")
        
        print(f"{Colors.GREEN}Created {len(jobs_created)} jobs{Colors.ENDC}")
        
        # Step 4: Generate matches
        print(f"\n{Colors.CYAN}Step 4: Generating job matches...{Colors.ENDC}")
        async with session.post(
            f"{base_url}/matching/generate",
            headers=headers
        ) as response:
            if response.status == 200:
                match_result = await response.json()
                print(f"{Colors.GREEN}✅ Matching completed{Colors.ENDC}")
                print(f"  Matches generated: {match_result.get('matches_created', 0)}")
            else:
                print(f"{Colors.FAIL}❌ Matching failed{Colors.ENDC}")
        
        # Step 5: Get matches
        print(f"\n{Colors.CYAN}Step 5: Retrieving matches...{Colors.ENDC}")
        async with session.get(
            f"{base_url}/matches/?min_score=0",
            headers=headers
        ) as response:
            if response.status == 200:
                matches = await response.json()
                print(f"{Colors.GREEN}✅ Retrieved {len(matches)} matches{Colors.ENDC}")
                
                # Display top matches
                if matches:
                    print(f"\n{Colors.CYAN}Top Matches:{Colors.ENDC}")
                    for i, match in enumerate(matches[:3], 1):
                        print(f"\n  {i}. {match.get('job', {}).get('title', 'Unknown')}")
                        print(f"     Company: {match.get('job', {}).get('company', 'Unknown')}")
                        print(f"     Score: {match.get('score', 0):.1f}%")
                        print(f"     Status: {match.get('status', 'unknown')}")
                        
                        # Show score breakdown if available
                        breakdown = match.get('score_breakdown', {})
                        if breakdown:
                            print(f"     Breakdown:")
                            for key, value in breakdown.items():
                                print(f"       - {key}: {value:.1f}")
            else:
                print(f"{Colors.FAIL}❌ Failed to retrieve matches{Colors.ENDC}")
        
        print(f"\n{Colors.GREEN}✅ Matching flow test completed!{Colors.ENDC}\n")


async def main():
    """Run the test."""
    await test_matching_flow()


if __name__ == "__main__":
    asyncio.run(main())