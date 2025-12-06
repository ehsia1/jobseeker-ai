#!/usr/bin/env python3
"""Test script for job matching system."""

import asyncio
import sys
import os
from pathlib import Path
import json

# Add backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def main():
    """Test the matching system."""
    
    print("🎯 Testing JobSeeker AI Matching System...")
    
    try:
        # Import after path setup
        from backend.config import settings
        from backend.database import async_session
        from backend.services.matching_service import MatchingService
        from backend.scorers.job_scorer import JobScorer
        from backend.scorers.embedding_service import EmbeddingService
        
        print(f"Environment: {settings.environment}")
        print()
        
        # Test embedding service
        print("🧠 Testing Embedding Service...")
        embedding_service = EmbeddingService(model_type="local")
        
        # Test text
        test_text = "Python developer with AWS Lambda and serverless experience"
        embedding = await embedding_service.generate_embedding(test_text)
        print(f"✅ Generated embedding (dimension: {embedding.shape[0]})")
        
        # Test similarity
        text1 = "Python backend developer with cloud experience"
        text2 = "Full-stack Python engineer with AWS skills"
        text3 = "Frontend React developer"
        
        emb1 = await embedding_service.generate_embedding(text1)
        emb2 = await embedding_service.generate_embedding(text2)
        emb3 = await embedding_service.generate_embedding(text3)
        
        sim12 = embedding_service.calculate_similarity(emb1, emb2)
        sim13 = embedding_service.calculate_similarity(emb1, emb3)
        
        print(f"Similarity (Python ↔ Python/AWS): {sim12:.2f}")
        print(f"Similarity (Python ↔ React): {sim13:.2f}")
        print()
        
        # Test scorer
        print("📊 Testing Job Scorer...")
        scorer = JobScorer(embedding_service)
        
        # Sample job and profile
        sample_job = {
            "title": "Senior Python Developer",
            "company": "Tech Startup",
            "description": "We need a Python developer with AWS Lambda experience",
            "skills": ["python", "aws", "lambda", "docker"],
            "requirements": ["5+ years experience", "AWS certified"],
            "rate_min": 100,
            "rate_max": 150,
            "rate_type": "hourly",
            "remote": True
        }
        
        sample_profile = {
            "skills": ["python", "aws", "docker", "postgresql"],
            "experience_years": 6,
            "certifications": ["AWS Solutions Architect"],
            "preferences": {"remote_only": True, "industries": ["Tech", "SaaS"]},
            "min_rate_usd": 90,
            "max_hours_per_week": 40
        }
        
        scoring_result = await scorer.score(sample_job, sample_profile)
        
        print(f"Total Score: {scoring_result.total_score:.1f}/100")
        print(f"Confidence: {scoring_result.confidence:.2f}")
        print("\nScore Breakdown:")
        for component, score in scoring_result.breakdown.items():
            print(f"  {component}: {score:.1f}")
        print(f"\nExplanation: {scoring_result.explanation}")
        print()
        
        # Test with database
        print("💾 Testing Database Matching...")
        
        async with async_session() as db:
            matching_service = MatchingService(db)
            
            # Check for users
            from sqlalchemy import select
            from backend.models.user import User
            
            users_result = await db.execute(select(User).limit(1))
            user = users_result.scalar_one_or_none()
            
            if user:
                print(f"Found user: {user.username}")
                
                # Check for jobs
                from backend.models.job import Job
                jobs_result = await db.execute(select(Job).limit(5))
                jobs = jobs_result.scalars().all()
                
                if jobs:
                    print(f"Found {len(jobs)} jobs in database")
                    
                    # Test matching for first job
                    first_job = jobs[0]
                    print(f"\nSample job: {first_job.title[:50]}...")
                    
                    # Get user profile
                    from backend.models.user import UserProfile
                    profile_result = await db.execute(
                        select(UserProfile).where(UserProfile.user_id == user.id)
                    )
                    profile = profile_result.scalar_one_or_none()
                    
                    if profile:
                        # Score the match
                        job_dict = {
                            "title": first_job.title,
                            "company": first_job.company,
                            "description": first_job.description,
                            "skills": first_job.skills,
                            "requirements": first_job.requirements,
                            "rate_min": first_job.rate_min,
                            "rate_max": first_job.rate_max,
                            "rate_type": first_job.rate_type,
                            "remote": first_job.remote
                        }
                        
                        profile_dict = {
                            "skills": profile.skills,
                            "experience_years": profile.experience_years,
                            "certifications": profile.certifications,
                            "preferences": profile.preferences,
                            "min_rate_usd": profile.min_rate_usd
                        }
                        
                        result = await scorer.score(job_dict, profile_dict)
                        print(f"Match score: {result.total_score:.1f}/100")
                    else:
                        print("No profile found for user")
                else:
                    print("No jobs found in database")
            else:
                print("No users found - please create a test user first")
        
        print("\n✅ Matching system test complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)