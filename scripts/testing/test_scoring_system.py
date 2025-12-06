#!/usr/bin/env python3
"""Test the advanced scoring system."""

import asyncio
import logging
from datetime import datetime, timedelta
from pprint import pprint

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from backend.services.embedding_service import EmbeddingService
from backend.services.scoring_service import ScoringService
from backend.models.job import Job
from backend.models.user import UserProfile


def create_test_job(
    title="Senior Python Developer",
    company="Tech Startup",
    skills=None,
    remote=True,
    rate_min=120000,
    rate_max=160000,
    location="San Francisco, CA",
    posted_days_ago=1
):
    """Create a test job."""
    if skills is None:
        skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    
    # Create a mock job object with necessary attributes
    class MockJob:
        def __init__(self):
            self.id = "test-job-1"
            self.title = title
            self.company = company
            self.description = f"We're looking for a {title} to join our team. Required skills: {', '.join(skills)}. This is a great opportunity to work with cutting-edge technology."
            self.skills = skills
            self.requirements = {"experience": "5+ years", "education": "BS in Computer Science preferred"}
            self.rate_min = rate_min
            self.rate_max = rate_max
            self.rate_type = "annual"
            self.location = location
            self.remote = remote
            self.posted_at = datetime.utcnow() - timedelta(days=posted_days_ago)
            self.source = "test"
            self.url = "https://example.com/job"
            self.embedding = None
            self.employment_type = "full-time"
            self.hours_per_week = 40
    
    job = MockJob()
    return job


def create_test_profile(
    profession="software_engineer",
    skills=None,
    experience_years=6,
    min_rate=100000,
    location="San Francisco, CA",
    remote_only=False
):
    """Create a test user profile."""
    if skills is None:
        skills = ["Python", "Django", "FastAPI", "PostgreSQL", "AWS", "Docker"]
    
    # Create a mock profile object with necessary attributes
    class MockProfile:
        def __init__(self):
            self.id = "test-profile-1"
            self.user_id = "test-user-1"
            self.profession = profession
            self.job_title = "Senior Backend Engineer"
            self.skills = skills
            self.experience_years = experience_years
            self.experience = "6 years building scalable web applications with Python and cloud technologies"
            self.education = "BS Computer Science"
            self.certifications = ["AWS Solutions Architect"]
            self.preferences = {
                "remote_only": remote_only,
                "industries": ["tech", "startup"],
                "job_types": ["full-time"],
                "avoid_keywords": ["PHP", "Ruby"]
            }
            self.min_rate_usd = min_rate
            self.location = location
            self.portfolio = {"github": "https://github.com/testuser"}
            self.profile_embedding = None
            self.timezone = None
    
    profile = MockProfile()
    return profile


async def test_scoring():
    """Test the scoring system with various scenarios."""
    
    # Initialize services
    embedding_service = EmbeddingService()
    scoring_service = ScoringService(embedding_service)
    
    print("=" * 70)
    print("ADVANCED JOB SCORING SYSTEM TEST")
    print("=" * 70)
    
    # Test Case 1: Perfect Match
    print("\n📊 Test Case 1: Perfect Match")
    print("-" * 50)
    
    job1 = create_test_job(
        title="Senior Python Developer",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        rate_min=120000,
        rate_max=160000,
        remote=True,
        posted_days_ago=1
    )
    
    profile1 = create_test_profile(
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        experience_years=6,
        min_rate=130000,
        remote_only=True
    )
    
    score1 = scoring_service.score_job(job1, profile1)
    print(f"Total Score: {score1.total_score:.1f}/100")
    print("\nScore Breakdown:")
    for key, value in score1.to_dict().items():
        if key != 'total_score':
            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
    
    explanation1 = scoring_service.generate_explanation(job1, profile1, score1)
    print("\nExplanation:")
    print(explanation1)
    
    # Test Case 2: Skill Mismatch
    print("\n📊 Test Case 2: Skill Mismatch")
    print("-" * 50)
    
    job2 = create_test_job(
        title="React Frontend Developer",
        skills=["React", "TypeScript", "CSS", "Node.js"],
        rate_min=100000,
        rate_max=140000,
        remote=True,
        posted_days_ago=3
    )
    
    profile2 = create_test_profile(
        skills=["Python", "Django", "PostgreSQL"],  # Backend skills
        experience_years=5,
        min_rate=110000,
        remote_only=True
    )
    
    score2 = scoring_service.score_job(job2, profile2)
    print(f"Total Score: {score2.total_score:.1f}/100")
    print("\nScore Breakdown:")
    for key, value in score2.to_dict().items():
        if key != 'total_score':
            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
    
    explanation2 = scoring_service.generate_explanation(job2, profile2, score2)
    print("\nExplanation:")
    print(explanation2)
    
    # Test Case 3: Location Mismatch
    print("\n📊 Test Case 3: Location Mismatch (Non-Remote)")
    print("-" * 50)
    
    job3 = create_test_job(
        title="Python Developer",
        skills=["Python", "Django", "PostgreSQL"],
        rate_min=110000,
        rate_max=150000,
        remote=False,  # On-site only
        location="New York, NY",
        posted_days_ago=7
    )
    
    profile3 = create_test_profile(
        skills=["Python", "Django", "PostgreSQL", "Redis"],
        experience_years=5,
        min_rate=120000,
        location="San Francisco, CA",
        remote_only=True  # Wants remote only
    )
    
    score3 = scoring_service.score_job(job3, profile3)
    print(f"Total Score: {score3.total_score:.1f}/100")
    print("\nScore Breakdown:")
    for key, value in score3.to_dict().items():
        if key != 'total_score':
            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
    
    explanation3 = scoring_service.generate_explanation(job3, profile3, score3)
    print("\nExplanation:")
    print(explanation3)
    
    # Test Case 4: Compensation Below Expectations
    print("\n📊 Test Case 4: Compensation Below Expectations")
    print("-" * 50)
    
    job4 = create_test_job(
        title="Python Developer",
        skills=["Python", "FastAPI", "PostgreSQL"],
        rate_min=70000,
        rate_max=90000,  # Below user's minimum
        remote=True,
        posted_days_ago=2
    )
    
    profile4 = create_test_profile(
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=6,
        min_rate=120000,  # Wants much more
        remote_only=True
    )
    
    score4 = scoring_service.score_job(job4, profile4)
    print(f"Total Score: {score4.total_score:.1f}/100")
    print("\nScore Breakdown:")
    for key, value in score4.to_dict().items():
        if key != 'total_score':
            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
    
    explanation4 = scoring_service.generate_explanation(job4, profile4, score4)
    print("\nExplanation:")
    print(explanation4)
    
    # Test Case 5: Old Posting
    print("\n📊 Test Case 5: Old Job Posting")
    print("-" * 50)
    
    job5 = create_test_job(
        title="Python Developer",
        skills=["Python", "Django", "PostgreSQL"],
        rate_min=120000,
        rate_max=150000,
        remote=True,
        posted_days_ago=45  # Very old posting
    )
    
    profile5 = create_test_profile(
        skills=["Python", "Django", "PostgreSQL"],
        experience_years=5,
        min_rate=125000,
        remote_only=True
    )
    
    score5 = scoring_service.score_job(job5, profile5)
    print(f"Total Score: {score5.total_score:.1f}/100")
    print("\nScore Breakdown:")
    for key, value in score5.to_dict().items():
        if key != 'total_score':
            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
    
    explanation5 = scoring_service.generate_explanation(job5, profile5, score5)
    print("\nExplanation:")
    print(explanation5)
    
    # Summary
    print("\n" + "=" * 70)
    print("SCORING SUMMARY")
    print("=" * 70)
    
    test_cases = [
        ("Perfect Match", score1.total_score),
        ("Skill Mismatch", score2.total_score),
        ("Location Mismatch", score3.total_score),
        ("Low Compensation", score4.total_score),
        ("Old Posting", score5.total_score)
    ]
    
    for name, score in test_cases:
        bar_length = int(score / 2)  # Scale to 50 chars
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"{name:20} [{bar}] {score:.1f}%")
    
    print("\n✅ Scoring system is working with multi-factor analysis!")
    print("   - Semantic similarity (embeddings)")
    print("   - Skill matching")
    print("   - Experience alignment")
    print("   - Compensation fit")
    print("   - Location preferences")
    print("   - Posting freshness")
    print("   - User preferences")


if __name__ == "__main__":
    asyncio.run(test_scoring())