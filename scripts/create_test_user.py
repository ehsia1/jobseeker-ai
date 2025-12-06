#!/usr/bin/env python3
"""Create a test user for the job search demo."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.models.user import User, UserProfile
from backend.api.routes.auth import get_password_hash

async def create_test_user():
    """Create a test user with profile."""
    
    # Create database connection
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return
    
    engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(
            select(User).where(User.username == "testuser")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"User 'testuser' already exists with ID: {existing_user.id}")
            user = existing_user
        else:
            # Create new user
            user = User(
                email="test@example.com",
                username="testuser",
                password_hash=get_password_hash("testpass123"),
                is_active=True,
                is_premium=True
            )
            db.add(user)
            await db.flush()
            print(f"Created user 'testuser' with ID: {user.id}")
        
        # Check if profile exists
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        existing_profile = profile_result.scalar_one_or_none()
        
        if existing_profile:
            print(f"Profile already exists for user")
            # Update profile with tech skills
            existing_profile.skills = [
                "Python", "FastAPI", "Django", "Flask",
                "JavaScript", "TypeScript", "React", "Node.js",
                "PostgreSQL", "MongoDB", "Redis",
                "Docker", "Kubernetes", "AWS", "GCP",
                "Machine Learning", "Deep Learning", "NLP"
            ]
            existing_profile.preferences = {
                "remote_only": True,
                "job_types": ["full-time", "contract"],
                "min_salary": 100000,
                "max_salary": 200000
            }
            existing_profile.experience = "5+ years in backend development, 3+ years in ML/AI"
            existing_profile.education = "B.S. Computer Science"
            existing_profile.certifications = ["AWS Solutions Architect", "Google Cloud Professional"]
            existing_profile.min_rate_usd = 100000
            existing_profile.location = "San Francisco, CA"
            existing_profile.timezone = "America/Los_Angeles"
            await db.flush()
            print("Updated profile with skills and preferences")
        else:
            # Create profile
            profile = UserProfile(
                user_id=user.id,
                skills=[
                    "Python", "FastAPI", "Django", "Flask",
                    "JavaScript", "TypeScript", "React", "Node.js",
                    "PostgreSQL", "MongoDB", "Redis",
                    "Docker", "Kubernetes", "AWS", "GCP",
                    "Machine Learning", "Deep Learning", "NLP"
                ],
                preferences={
                    "remote_only": True,
                    "job_types": ["full-time", "contract"],
                    "min_salary": 100000,
                    "max_salary": 200000
                },
                experience="5+ years in backend development, 3+ years in ML/AI",
                education="B.S. Computer Science",
                certifications=["AWS Solutions Architect", "Google Cloud Professional"],
                min_rate_usd=100000,
                location="San Francisco, CA",
                timezone="America/Los_Angeles"
            )
            db.add(profile)
            await db.flush()
            print("Created profile with skills and preferences")
        
        await db.commit()
        print("\n✓ Test user setup complete!")
        print("  Username: testuser")
        print("  Password: testpass123")
        print(f"  Skills: {len(profile.skills if not existing_profile else existing_profile.skills)} skills configured")
        

if __name__ == "__main__":
    asyncio.run(create_test_user())