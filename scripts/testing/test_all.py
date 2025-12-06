#!/usr/bin/env python3
"""Comprehensive test script for the entire JobSeeker AI system."""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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


async def test_database_connection():
    """Test database connectivity."""
    print(f"\n{Colors.HEADER}=== Testing Database Connection ==={Colors.ENDC}")
    
    try:
        from backend.database import async_session
        from sqlalchemy import text
        
        async with async_session() as db:
            result = await db.execute(text("SELECT 1"))
            print(f"{Colors.GREEN}✅ Database connected successfully{Colors.ENDC}")
            
            # Check tables
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'jobseeker'
                ORDER BY table_name
            """)
            tables_result = await db.execute(tables_query)
            tables = [row[0] for row in tables_result.all()]
            
            if tables:
                print(f"{Colors.CYAN}📊 Found {len(tables)} tables:{Colors.ENDC}")
                for table in tables:
                    print(f"   - {table}")
            else:
                print(f"{Colors.WARNING}⚠️  No tables found - run migrations first{Colors.ENDC}")
                return False
                
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Database connection failed: {e}{Colors.ENDC}")
        return False


async def test_api_server():
    """Test if API server is running."""
    print(f"\n{Colors.HEADER}=== Testing API Server ==={Colors.ENDC}")
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health/")
            
            if response.status_code == 200:
                data = response.json()
                print(f"{Colors.GREEN}✅ API server is running{Colors.ENDC}")
                print(f"   Version: {data.get('version')}")
                print(f"   Environment: {data.get('environment')}")
                return True
            else:
                print(f"{Colors.WARNING}⚠️  API returned status {response.status_code}{Colors.ENDC}")
                return False
                
    except Exception as e:
        print(f"{Colors.WARNING}⚠️  API server not reachable - start with 'make dev-server'{Colors.ENDC}")
        return False


async def test_authentication():
    """Test user registration and login."""
    print(f"\n{Colors.HEADER}=== Testing Authentication ==={Colors.ENDC}")
    
    try:
        import httpx
        from datetime import datetime
        
        async with httpx.AsyncClient() as client:
            # Try to register a test user
            test_user = {
                "email": f"test_{datetime.now().timestamp()}@example.com",
                "username": f"testuser_{int(datetime.now().timestamp())}",
                "password": "TestPassword123!"
            }
            
            # Register
            register_response = await client.post(
                "http://localhost:8080/auth/register",
                json=test_user
            )
            
            if register_response.status_code == 200:
                user_data = register_response.json()
                print(f"{Colors.GREEN}✅ User registration successful{Colors.ENDC}")
                print(f"   User ID: {user_data['id']}")
                
                # Login
                login_response = await client.post(
                    "http://localhost:8080/auth/login",
                    data={
                        "username": test_user["username"],
                        "password": test_user["password"]
                    }
                )
                
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    token = login_data.get("access_token")
                    print(f"{Colors.GREEN}✅ Login successful{Colors.ENDC}")
                    print(f"   Token: {token[:20]}...")
                    return token
                else:
                    print(f"{Colors.WARNING}⚠️  Login failed{Colors.ENDC}")
                    
            elif register_response.status_code == 400:
                print(f"{Colors.CYAN}ℹ️  User already exists - using existing account{Colors.ENDC}")
                # Try login with default test account
                login_response = await client.post(
                    "http://localhost:8080/auth/login",
                    data={
                        "username": "testuser",
                        "password": "testpass123"
                    }
                )
                if login_response.status_code == 200:
                    return login_response.json().get("access_token")
                    
    except Exception as e:
        print(f"{Colors.WARNING}⚠️  Authentication test failed: {e}{Colors.ENDC}")
        
    return None


async def test_job_ingestion():
    """Test job ingestion pipeline."""
    print(f"\n{Colors.HEADER}=== Testing Job Ingestion ==={Colors.ENDC}")
    
    try:
        from backend.database import async_session
        from backend.services.ingestion_service import IngestionService
        
        async with async_session() as db:
            ingestion_service = IngestionService(db)
            
            # Test parsers
            print(f"{Colors.CYAN}🔍 Testing parsers...{Colors.ENDC}")
            test_results = await ingestion_service.test_parsers()
            
            # Check email parsers
            email_parsers = test_results.get("email_parsers", {})
            if email_parsers:
                for parser, result in email_parsers.items():
                    if result["status"] == "success":
                        print(f"{Colors.GREEN}✅ {parser} email parser OK{Colors.ENDC}")
                    else:
                        print(f"{Colors.WARNING}⚠️  {parser}: {result.get('error', 'Failed')}{Colors.ENDC}")
            
            # Check RSS parsers
            rss_parsers = test_results.get("rss_parsers", {})
            for parser, result in rss_parsers.items():
                if result["status"] == "success":
                    print(f"{Colors.GREEN}✅ {parser} RSS parser OK{Colors.ENDC}")
                    if result.get("jobs_parsed", 0) > 0:
                        print(f"   📋 Found {result['jobs_parsed']} jobs")
                else:
                    print(f"{Colors.WARNING}⚠️  {parser}: {result.get('error', 'Failed')}{Colors.ENDC}")
            
            # Check job count
            from sqlalchemy import select, func
            from backend.models.job import Job
            
            count_result = await db.execute(select(func.count(Job.id)))
            job_count = count_result.scalar() or 0
            
            print(f"\n{Colors.CYAN}📊 Total jobs in database: {job_count}{Colors.ENDC}")
            
            if job_count == 0:
                print(f"{Colors.WARNING}ℹ️  No jobs found - run ingestion to populate{Colors.ENDC}")
                
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ingestion test failed: {e}{Colors.ENDC}")
        return False


async def test_matching_system():
    """Test job matching and scoring."""
    print(f"\n{Colors.HEADER}=== Testing Matching System ==={Colors.ENDC}")
    
    try:
        from backend.scorers.embedding_service import EmbeddingService
        from backend.scorers.job_scorer import JobScorer
        
        # Test embeddings
        print(f"{Colors.CYAN}🧠 Testing embeddings...{Colors.ENDC}")
        embedding_service = EmbeddingService(model_type="local")
        
        test_text = "Python developer with AWS experience"
        embedding = await embedding_service.generate_embedding(test_text)
        print(f"{Colors.GREEN}✅ Embedding generation OK (dim: {embedding.shape[0]}){Colors.ENDC}")
        
        # Test similarity
        text1 = "Python backend developer"
        text2 = "Python engineer"
        text3 = "Java developer"
        
        emb1 = await embedding_service.generate_embedding(text1)
        emb2 = await embedding_service.generate_embedding(text2)
        emb3 = await embedding_service.generate_embedding(text3)
        
        sim_similar = embedding_service.calculate_similarity(emb1, emb2)
        sim_different = embedding_service.calculate_similarity(emb1, emb3)
        
        print(f"   Similar texts: {sim_similar:.2f}")
        print(f"   Different texts: {sim_different:.2f}")
        
        if sim_similar > sim_different:
            print(f"{Colors.GREEN}✅ Similarity calculation working correctly{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️  Similarity scores unexpected{Colors.ENDC}")
        
        # Test scorer
        print(f"\n{Colors.CYAN}📊 Testing job scorer...{Colors.ENDC}")
        scorer = JobScorer(embedding_service)
        
        sample_job = {
            "title": "Python Developer",
            "skills": ["python", "aws"],
            "remote": True,
            "rate_min": 100
        }
        
        sample_profile = {
            "skills": ["python", "docker"],
            "preferences": {"remote_only": True},
            "min_rate_usd": 80
        }
        
        result = await scorer.score(sample_job, sample_profile)
        print(f"{Colors.GREEN}✅ Scoring completed{Colors.ENDC}")
        print(f"   Score: {result.total_score:.1f}/100")
        print(f"   Confidence: {result.confidence:.2f}")
        
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Matching test failed: {e}{Colors.ENDC}")
        return False


async def test_with_sample_data():
    """Create and test with sample data."""
    print(f"\n{Colors.HEADER}=== Testing with Sample Data ==={Colors.ENDC}")
    
    try:
        from backend.database import async_session
        from backend.models.user import User, UserProfile
        from backend.models.job import Job
        from backend.services.matching_service import MatchingService
        from sqlalchemy import select
        
        async with async_session() as db:
            # Check for existing user
            user_result = await db.execute(
                select(User).where(User.username == "testuser")
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                print(f"{Colors.CYAN}Creating test user...{Colors.ENDC}")
                from backend.api.routes.auth import get_password_hash
                
                user = User(
                    email="test@example.com",
                    username="testuser",
                    password_hash=get_password_hash("testpass123")
                )
                db.add(user)
                await db.commit()
                
                # Create profile
                profile = UserProfile(
                    user_id=user.id,
                    skills=["python", "aws", "docker", "postgresql"],
                    experience_years=5,
                    preferences={"remote_only": True},
                    min_rate_usd=80
                )
                db.add(profile)
                await db.commit()
                print(f"{Colors.GREEN}✅ Test user created{Colors.ENDC}")
            else:
                print(f"{Colors.CYAN}Using existing test user{Colors.ENDC}")
            
            # Check for jobs
            jobs_result = await db.execute(select(Job).limit(5))
            jobs = jobs_result.scalars().all()
            
            if not jobs:
                print(f"{Colors.CYAN}Creating sample jobs...{Colors.ENDC}")
                
                sample_jobs = [
                    Job(
                        source="test",
                        title="Senior Python Developer",
                        company="Tech Corp",
                        description="Looking for Python expert with cloud experience",
                        skills=["python", "aws", "docker"],
                        remote=True,
                        rate_min=100,
                        rate_max=150,
                        rate_type="hourly"
                    ),
                    Job(
                        source="test",
                        title="Full Stack Engineer",
                        company="Startup Inc",
                        description="Node.js and React developer needed",
                        skills=["javascript", "react", "node.js"],
                        remote=True,
                        rate_min=80,
                        rate_max=120,
                        rate_type="hourly"
                    ),
                    Job(
                        source="test",
                        title="DevOps Engineer",
                        company="Cloud Systems",
                        description="AWS and Kubernetes expert wanted",
                        skills=["aws", "kubernetes", "terraform"],
                        remote=False,
                        rate_min=110,
                        rate_max=160,
                        rate_type="hourly"
                    )
                ]
                
                for job in sample_jobs:
                    db.add(job)
                
                await db.commit()
                print(f"{Colors.GREEN}✅ Sample jobs created{Colors.ENDC}")
                jobs = sample_jobs
            
            # Test matching
            print(f"\n{Colors.CYAN}🎯 Running job matching...{Colors.ENDC}")
            matching_service = MatchingService(db)
            
            matches = await matching_service.generate_matches_for_user(
                user_id=str(user.id),
                limit=10,
                min_score=50.0  # Lower threshold for testing
            )
            
            if matches:
                print(f"{Colors.GREEN}✅ Generated {len(matches)} matches{Colors.ENDC}")
                
                # Show top matches
                print(f"\n{Colors.CYAN}Top Matches:{Colors.ENDC}")
                for i, match in enumerate(matches[:3], 1):
                    # Get job details
                    job_result = await db.execute(
                        select(Job).where(Job.id == match.job_id)
                    )
                    job = job_result.scalar_one()
                    
                    print(f"\n  {i}. {job.title} @ {job.company or 'Unknown'}")
                    print(f"     Score: {match.score:.1f}/100")
                    print(f"     Skills: {', '.join(job.skills[:3]) if job.skills else 'N/A'}")
                    print(f"     Rate: ${job.rate_min}-${job.rate_max} {job.rate_type or ''}")
                    print(f"     Explanation: {match.explanation}")
            else:
                print(f"{Colors.WARNING}ℹ️  No matches generated{Colors.ENDC}")
                
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Sample data test failed: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("       JobSeeker AI - Comprehensive System Test")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    
    # Track results
    results = {}
    
    # Test database
    results['database'] = await test_database_connection()
    
    if not results['database']:
        print(f"\n{Colors.FAIL}❌ Database not available - please run 'docker-compose up -d'{Colors.ENDC}")
        return 1
    
    # Test API
    results['api'] = await test_api_server()
    
    if results['api']:
        # Test authentication
        token = await test_authentication()
        results['auth'] = token is not None
    else:
        print(f"\n{Colors.WARNING}ℹ️  Skipping API tests - server not running{Colors.ENDC}")
    
    # Test ingestion
    results['ingestion'] = await test_job_ingestion()
    
    # Test matching
    results['matching'] = await test_matching_system()
    
    # Test with sample data
    results['sample'] = await test_with_sample_data()
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== Test Summary ==={Colors.ENDC}")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for component, passed in results.items():
        status = f"{Colors.GREEN}✅ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
        print(f"  {component.capitalize()}: {status}")
    
    print(f"\n{Colors.BOLD}Result: {passed_tests}/{total_tests} tests passed{Colors.ENDC}")
    
    if passed_tests == total_tests:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All systems operational!{Colors.ENDC}")
        return 0
    else:
        print(f"{Colors.WARNING}⚠️  Some components need attention{Colors.ENDC}")
        print(f"\n{Colors.CYAN}Next steps:{Colors.ENDC}")
        
        if not results.get('api'):
            print("  1. Start API server: make dev-server")
        if not results.get('ingestion'):
            print("  2. Configure email in .env file")
        if not results.get('sample'):
            print("  3. Run migrations: make migrate")
            
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)