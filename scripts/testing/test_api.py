#!/usr/bin/env python3
"""Test API endpoints."""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def test_api_endpoints():
    """Test basic API endpoints."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}JobSeeker AI - API Endpoint Tests{Colors.ENDC}")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print(f"\n{Colors.CYAN}Testing Health Endpoint:{Colors.ENDC}")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"{Colors.GREEN}✅ Health check passed{Colors.ENDC}")
                    print(f"  Status: {data.get('status', 'unknown')}")
                    print(f"  Database: {data.get('database', 'unknown')}")
                    print(f"  Redis: {data.get('redis', 'unknown')}")
                else:
                    print(f"{Colors.FAIL}❌ Health check failed (status: {response.status}){Colors.ENDC}")
        except aiohttp.ClientError as e:
            print(f"{Colors.FAIL}❌ Could not connect to API: {e}{Colors.ENDC}")
            print(f"\n{Colors.WARNING}Is the backend running?{Colors.ENDC}")
            print("  Start it with: docker-compose up backend")
            return False
        
        # Test user registration
        print(f"\n{Colors.CYAN}Testing User Registration:{Colors.ENDC}")
        test_user = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123!"
        }
        
        try:
            async with session.post(
                f"{base_url}/auth/register",
                json=test_user
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"{Colors.GREEN}✅ User registration successful{Colors.ENDC}")
                    print(f"  User ID: {data.get('id', 'unknown')}")
                    print(f"  Username: {data.get('username', 'unknown')}")
                elif response.status == 409:
                    print(f"{Colors.WARNING}⚠️  User already exists{Colors.ENDC}")
                else:
                    error_text = await response.text()
                    print(f"{Colors.FAIL}❌ Registration failed (status: {response.status}){Colors.ENDC}")
                    print(f"  Error: {error_text}")
        except aiohttp.ClientError as e:
            print(f"{Colors.FAIL}❌ Registration request failed: {e}{Colors.ENDC}")
        
        # Test user login
        print(f"\n{Colors.CYAN}Testing User Login:{Colors.ENDC}")
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        try:
            async with session.post(
                f"{base_url}/auth/login",
                data=login_data  # OAuth2 expects form data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get('access_token')
                    print(f"{Colors.GREEN}✅ Login successful{Colors.ENDC}")
                    print(f"  Token type: {data.get('token_type', 'unknown')}")
                    print(f"  Token: {token[:20]}..." if token else "  No token")
                    return token
                else:
                    error_text = await response.text()
                    print(f"{Colors.FAIL}❌ Login failed (status: {response.status}){Colors.ENDC}")
                    print(f"  Error: {error_text}")
        except aiohttp.ClientError as e:
            print(f"{Colors.FAIL}❌ Login request failed: {e}{Colors.ENDC}")
        
        # Test jobs endpoint (requires auth)
        if 'token' in locals():
            print(f"\n{Colors.CYAN}Testing Jobs Endpoint (Authenticated):{Colors.ENDC}")
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                async with session.get(
                    f"{base_url}/jobs/",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"{Colors.GREEN}✅ Jobs endpoint accessible{Colors.ENDC}")
                        print(f"  Jobs found: {len(data) if isinstance(data, list) else 'unknown'}")
                    else:
                        print(f"{Colors.FAIL}❌ Jobs request failed (status: {response.status}){Colors.ENDC}")
            except aiohttp.ClientError as e:
                print(f"{Colors.FAIL}❌ Jobs request failed: {e}{Colors.ENDC}")
    
    print(f"\n{Colors.GREEN}API tests completed!{Colors.ENDC}\n")
    return True


async def main():
    """Run API tests."""
    success = await test_api_endpoints()
    
    if success:
        print(f"{Colors.GREEN}Next steps:{Colors.ENDC}")
        print("  1. Test job ingestion: python scripts/test_ingestion.py")
        print("  2. Test job matching: python scripts/test_matching.py")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)