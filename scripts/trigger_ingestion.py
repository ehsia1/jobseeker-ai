#!/usr/bin/env python3
"""Trigger job ingestion via API."""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

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


async def trigger_ingestion():
    """Trigger job ingestion through the API."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}JobSeeker AI - Ingestion Trigger{Colors.ENDC}")
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
        
        # Step 2: Check ingestion status
        print(f"\n{Colors.CYAN}Step 2: Checking ingestion status...{Colors.ENDC}")
        async with session.get(
            f"{base_url}/ingestion/status",
            headers=headers
        ) as response:
            if response.status == 200:
                status = await response.json()
                print(f"{Colors.GREEN}✅ Status retrieved{Colors.ENDC}")
                print(f"  Total jobs in system: {status.get('total_jobs', 0)}")
                print(f"  Recent jobs (24h): {status.get('recent_jobs', 0)}")
            else:
                print(f"{Colors.WARNING}⚠️  Could not get status{Colors.ENDC}")
        
        # Step 3: Trigger ingestion
        print(f"\n{Colors.CYAN}Step 3: Triggering job ingestion...{Colors.ENDC}")
        
        # Check if email credentials are configured
        email_configured = os.getenv("EMAIL_PASSWORD") and os.getenv("EMAIL_PASSWORD") != "your_app_specific_password"
        
        if not email_configured:
            print(f"{Colors.WARNING}⚠️  Email not configured!{Colors.ENDC}")
            print("\nTo configure email ingestion:")
            print("1. Follow instructions in GMAIL_SETUP.md")
            print("2. Add your Gmail app password to .env")
            print("3. Run this script again")
            print("\nFor now, testing with RSS feeds only...")
        
        async with session.post(
            f"{base_url}/ingestion/trigger",
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"{Colors.GREEN}✅ Ingestion triggered{Colors.ENDC}")
                
                # Show results
                if "email_results" in result:
                    print(f"\n{Colors.CYAN}Email Ingestion Results:{Colors.ENDC}")
                    for source, data in result.get("email_results", {}).items():
                        print(f"  {source}:")
                        print(f"    Emails processed: {data.get('emails_processed', 0)}")
                        print(f"    Jobs found: {data.get('jobs_parsed', 0)}")
                        print(f"    Jobs stored: {data.get('jobs_stored', 0)}")
                        if "error" in data:
                            print(f"    {Colors.FAIL}Error: {data['error']}{Colors.ENDC}")
                
                if "rss_results" in result:
                    print(f"\n{Colors.CYAN}RSS Feed Results:{Colors.ENDC}")
                    for source, data in result.get("rss_results", {}).items():
                        print(f"  {source}:")
                        print(f"    Jobs found: {data.get('jobs_parsed', 0)}")
                        print(f"    Jobs stored: {data.get('jobs_stored', 0)}")
                        if "error" in data:
                            print(f"    {Colors.FAIL}Error: {data['error']}{Colors.ENDC}")
                
                total_jobs = result.get("total_jobs", 0)
                print(f"\n{Colors.GREEN}Total new jobs ingested: {total_jobs}{Colors.ENDC}")
                
                if result.get("errors"):
                    print(f"\n{Colors.WARNING}Errors encountered:{Colors.ENDC}")
                    for error in result["errors"]:
                        print(f"  - {error}")
            else:
                error_text = await response.text()
                print(f"{Colors.FAIL}❌ Ingestion failed{Colors.ENDC}")
                print(f"  Error: {error_text}")
        
        # Step 4: Generate matches for the new jobs
        if email_configured:
            print(f"\n{Colors.CYAN}Step 4: Generating matches for new jobs...{Colors.ENDC}")
            async with session.post(
                f"{base_url}/matching/generate",
                headers=headers
            ) as response:
                if response.status == 200:
                    match_result = await response.json()
                    print(f"{Colors.GREEN}✅ Matching completed{Colors.ENDC}")
                    print(f"  Matches created: {match_result.get('matches_created', 0)}")
                else:
                    print(f"{Colors.WARNING}⚠️  Matching failed{Colors.ENDC}")
            
            # Step 5: Show top matches
            print(f"\n{Colors.CYAN}Step 5: Your top job matches...{Colors.ENDC}")
            async with session.get(
                f"{base_url}/matches/?min_score=70&limit=5",
                headers=headers
            ) as response:
                if response.status == 200:
                    matches = await response.json()
                    if matches:
                        for i, match in enumerate(matches, 1):
                            job = match.get('job', {})
                            print(f"\n  {i}. {job.get('title', 'Unknown')}")
                            print(f"     Company: {job.get('company', 'Unknown')}")
                            print(f"     Score: {match.get('score', 0):.1f}%")
                            print(f"     Rate: ${job.get('rate_min', 0)}-${job.get('rate_max', 0)} {job.get('rate_type', '')}")
                            if job.get('url'):
                                print(f"     URL: {job['url']}")
                    else:
                        print(f"  {Colors.WARNING}No high-scoring matches found{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}❌ Could not retrieve matches{Colors.ENDC}")
    
    print(f"\n{Colors.GREEN}✅ Ingestion process completed!{Colors.ENDC}\n")


async def main():
    """Run the ingestion trigger."""
    await trigger_ingestion()


if __name__ == "__main__":
    asyncio.run(main())