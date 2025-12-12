"""
Pytest fixtures and test configuration for JobSeeker AI.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy import create_engine, text, event, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB

from backend.database import Base, get_db


# =============================================================================
# SQLite Compatibility
# =============================================================================

def convert_jsonb_to_json_for_sqlite():
    """Convert JSONB columns to JSON for SQLite compatibility.

    This allows PostgreSQL models with JSONB columns to work with SQLite in tests.
    Call this before creating tables with SQLite.
    """
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()


from backend.config import Settings
from backend.models.user import User, UserProfile
from backend.models.job import Job, JobMatch
from backend.models.resume import Resume, WorkExperience
from backend.models.notification import Notification
from backend.models.subscription import Subscription

fake = Faker()


# =============================================================================
# Test Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with mocked values."""
    return Settings(
        environment="test",
        debug=True,
        secret_key="test-secret-key-for-testing-only",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        llm_provider="mock",
        demo_mode=True,
    )


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def async_engine():
    """Create async test database engine."""
    # Convert JSONB to JSON for SQLite compatibility
    convert_jsonb_to_json_for_sqlite()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        # Translate PostgreSQL schema to None for SQLite
        execution_options={"schema_translate_map": {"jobseeker": None}},
    )

    async with engine.begin() as conn:
        # Use schema_translate_map when creating tables
        await conn.run_sync(
            Base.metadata.create_all,
        )

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# =============================================================================
# Mock Services
# =============================================================================

@dataclass
class MockLLMResponse:
    """Mock response object matching LLMResponse interface."""
    content: str
    model: str = "mock-model"
    provider: str = "mock"
    usage: dict = field(default_factory=dict)


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for tests."""
    mock = MagicMock()

    async def mock_generate(prompt: str, system_prompt: str = None) -> MockLLMResponse:
        return MockLLMResponse(
            content="This is a mock LLM response for testing purposes. I have 5 years of experience in Python development and have successfully delivered multiple projects using FastAPI and PostgreSQL."
        )

    async def mock_generate_structured(prompt: str, system_prompt: str = None) -> dict:
        return {
            "full_name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "location": fake.city(),
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "summary": fake.text(max_nb_chars=200),
            "work_experiences": [
                {
                    "company": fake.company(),
                    "title": "Software Engineer",
                    "start_date": "2020-01-01",
                    "end_date": "2023-12-31",
                    "is_current": False,
                    "description": fake.text(max_nb_chars=100),
                    "achievements": [fake.sentence() for _ in range(3)],
                    "skills_used": ["Python", "FastAPI"],
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "school": fake.company(),
                    "year": "2019",
                }
            ],
            "certifications": ["AWS Solutions Architect"],
            "languages": ["English"],
            "parse_quality_score": 85,
        }

    mock.generate = AsyncMock(side_effect=mock_generate)
    mock.generate_structured = AsyncMock(side_effect=mock_generate_structured)
    mock.generate_with_context = AsyncMock(side_effect=mock_generate)

    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for tests."""
    import numpy as np

    mock = MagicMock()

    def mock_generate_embedding(text: str) -> np.ndarray:
        # Return deterministic mock embedding based on text hash
        np.random.seed(hash(text) % 2**32)
        return np.random.rand(1536).astype(np.float32)

    def mock_calculate_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        # Calculate actual cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm_product = np.linalg.norm(emb1) * np.linalg.norm(emb2)
        return float(dot_product / norm_product) if norm_product > 0 else 0.0

    mock.generate_embedding = MagicMock(side_effect=mock_generate_embedding)
    mock.generate_job_embedding = MagicMock(side_effect=lambda j: mock_generate_embedding(str(j)))
    mock.generate_profile_embedding = MagicMock(side_effect=lambda p: mock_generate_embedding(str(p)))
    mock.calculate_similarity = MagicMock(side_effect=mock_calculate_similarity)

    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests."""
    mock = MagicMock()
    cache = {}

    async def mock_get(key: str):
        return cache.get(key)

    async def mock_set(key: str, value: str, ex: int = None):
        cache[key] = value

    async def mock_delete(key: str):
        cache.pop(key, None)

    mock.get = AsyncMock(side_effect=mock_get)
    mock.set = AsyncMock(side_effect=mock_set)
    mock.delete = AsyncMock(side_effect=mock_delete)

    return mock


# =============================================================================
# Model Factories
# =============================================================================

@pytest.fixture
def user_factory(db_session: AsyncSession):
    """Factory for creating test users."""
    async def create_user(
        email: str = None,
        username: str = None,
        is_active: bool = True,
        is_premium: bool = False,
    ) -> User:
        user = User(
            id=uuid4(),
            email=email or fake.email(),
            username=username or fake.user_name(),
            password_hash="$2b$12$test_hash_for_testing_only",
            is_active=is_active,
            is_premium=is_premium,
        )
        db_session.add(user)
        await db_session.flush()
        return user

    return create_user


@pytest.fixture
def profile_factory(db_session: AsyncSession):
    """Factory for creating test user profiles."""
    async def create_profile(
        user: User,
        skills: list = None,
        experience_years: int = None,
        min_rate_usd: float = None,
        preferences: dict = None,
    ) -> UserProfile:
        profile = UserProfile(
            id=uuid4(),
            user_id=user.id,
            profession="software_engineer",
            job_title="Software Engineer",
            skills=skills or ["Python", "FastAPI", "PostgreSQL"],
            experience_years=experience_years or fake.random_int(min=1, max=15),
            min_rate_usd=Decimal(str(min_rate_usd)) if min_rate_usd else Decimal("100000"),
            preferences=preferences or {"remote_only": True},
        )
        db_session.add(profile)
        await db_session.flush()
        return profile

    return create_profile


@pytest.fixture
def job_factory(db_session: AsyncSession):
    """Factory for creating test jobs."""
    async def create_job(
        title: str = None,
        company: str = None,
        description: str = None,
        skills: list = None,
        remote: bool = True,
        rate_min: float = None,
        rate_max: float = None,
        rate_type: str = "annual",
        location: str = None,
        posted_at: datetime = None,
    ) -> Job:
        job = Job(
            id=uuid4(),
            source="test",
            source_id=str(uuid4()),
            url=fake.url(),
            title=title or fake.job(),
            company=company or fake.company(),
            description=description or fake.text(max_nb_chars=500),
            requirements=["3+ years experience", "Python required"],
            skills=skills or ["Python", "FastAPI", "PostgreSQL"],
            rate_min=Decimal(str(rate_min)) if rate_min else Decimal("90000"),
            rate_max=Decimal(str(rate_max)) if rate_max else Decimal("130000"),
            rate_type=rate_type,
            location=location or fake.city(),
            remote=remote,
            posted_at=posted_at or datetime.utcnow(),
        )
        db_session.add(job)
        await db_session.flush()
        return job

    return create_job


@pytest.fixture
def resume_factory(db_session: AsyncSession):
    """Factory for creating test resumes."""
    async def create_resume(
        user: User,
        skills: list = None,
        work_experiences: list = None,
    ) -> Resume:
        resume = Resume(
            id=uuid4(),
            user_id=user.id,
            file_type="text",
            raw_text=fake.text(max_nb_chars=2000),
            full_name=fake.name(),
            email=user.email,
            phone=fake.phone_number(),
            location=fake.city(),
            skills=skills or ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            education=[{"degree": "BS Computer Science", "school": fake.company(), "year": "2019"}],
            certifications=["AWS Solutions Architect"],
            languages=["English"],
            parse_quality_score=85,
            parsed_at=datetime.utcnow(),
        )
        db_session.add(resume)

        # Add work experiences if provided
        if work_experiences:
            for exp_data in work_experiences:
                exp = WorkExperience(
                    id=uuid4(),
                    resume=resume,
                    **exp_data
                )
                db_session.add(exp)
        else:
            # Default work experience
            exp = WorkExperience(
                id=uuid4(),
                resume=resume,
                company=fake.company(),
                title="Software Engineer",
                start_date=date(2020, 1, 1),
                end_date=date(2023, 12, 31),
                is_current=False,
                description="Built scalable web applications",
                achievements=["Increased performance by 50%"],
                skills_used=["Python", "FastAPI"],
            )
            db_session.add(exp)

        await db_session.flush()
        return resume

    return create_resume


@pytest.fixture
def job_match_factory(db_session: AsyncSession):
    """Factory for creating test job matches."""
    async def create_job_match(
        user: User,
        job: Job,
        score: float = 85.0,
        status: str = "new",
    ) -> JobMatch:
        match = JobMatch(
            id=uuid4(),
            user_id=user.id,
            job_id=job.id,
            score=Decimal(str(score)),
            score_breakdown={
                "semantic_similarity": 80.0,
                "skill_match": 90.0,
                "experience_match": 85.0,
                "compensation_match": 75.0,
                "location_match": 100.0,
                "freshness_score": 90.0,
                "preference_match": 80.0,
            },
            explanation="Strong match based on skill overlap.",
            status=status,
        )
        db_session.add(match)
        await db_session.flush()
        return match

    return create_job_match


@pytest.fixture
def subscription_factory(db_session: AsyncSession):
    """Factory for creating test subscriptions."""
    from backend.models.subscription import SubscriptionTier

    async def create_subscription(
        user: User,
        tier: str = "free",
        proposal_count: int = 0,
        jd_parse_count: int = 0,
        job_search_count_today: int = 0,
        stripe_customer_id: str = None,
        stripe_subscription_id: str = None,
    ) -> Subscription:
        # Map string tier to enum
        tier_map = {
            "free": SubscriptionTier.FREE,
            "starter": SubscriptionTier.STARTER,
            "pro": SubscriptionTier.PRO,
            "power": SubscriptionTier.POWER,
        }
        tier_enum = tier_map.get(tier, SubscriptionTier.FREE)

        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            tier=tier_enum,
            proposal_count=proposal_count,
            jd_parse_count=jd_parse_count,
            job_search_count_today=job_search_count_today,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            usage_reset_date=date.today(),
            daily_reset_date=date.today(),
        )
        db_session.add(subscription)
        await db_session.flush()
        return subscription

    return create_subscription


# =============================================================================
# API Test Client
# =============================================================================

@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession, mock_llm_service):
    """Create test client with mocked dependencies."""
    from fastapi.testclient import TestClient
    from httpx import AsyncClient, ASGITransport
    from backend.api.main import app
    from backend.api.dependencies import get_current_user

    # Override database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Generate auth headers for testing authenticated endpoints.

    Note: The API's get_current_user looks up users by username,
    so `sub` should be the username, not the user ID.
    """
    from datetime import timedelta
    from jose import jwt
    from backend.config import settings

    def create_headers(username: str):
        payload = {
            "sub": username,
            "exp": datetime.utcnow() + timedelta(hours=24),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
        return {"Authorization": f"Bearer {token}"}

    return create_headers


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing parsing."""
    return """
    John Doe
    john.doe@email.com | (555) 123-4567 | San Francisco, CA
    LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

    SUMMARY
    Senior Software Engineer with 8+ years of experience building scalable
    web applications and distributed systems. Expert in Python, FastAPI, and cloud technologies.

    EXPERIENCE

    Senior Software Engineer | TechCorp Inc. | 2020 - Present
    - Led development of microservices architecture serving 1M+ users
    - Reduced API response time by 60% through optimization
    - Mentored team of 5 junior developers
    - Technologies: Python, FastAPI, PostgreSQL, Redis, AWS

    Software Engineer | StartupXYZ | 2017 - 2020
    - Built real-time data processing pipeline handling 10K events/second
    - Implemented CI/CD pipelines reducing deployment time by 80%
    - Technologies: Python, Django, Celery, Docker, Kubernetes

    EDUCATION
    B.S. Computer Science | Stanford University | 2017
    GPA: 3.8

    SKILLS
    Languages: Python, JavaScript, TypeScript, SQL
    Frameworks: FastAPI, Django, React, Node.js
    Databases: PostgreSQL, MongoDB, Redis
    Cloud: AWS, GCP, Docker, Kubernetes

    CERTIFICATIONS
    - AWS Solutions Architect Professional
    - Kubernetes Administrator (CKA)
    """


@pytest.fixture
def sample_job_description():
    """Sample job description for testing parsing."""
    return """
    Senior Python Developer

    Company: TechStartup Inc.
    Location: Remote (US)
    Salary: $140,000 - $180,000/year

    About the Role:
    We're looking for a Senior Python Developer to join our growing team.
    You'll be responsible for building and maintaining our core platform.

    Requirements:
    - 5+ years of experience with Python
    - Strong experience with FastAPI or Django
    - Experience with PostgreSQL and Redis
    - Familiarity with AWS services
    - Experience with Docker and Kubernetes

    Nice to have:
    - Experience with machine learning
    - Contributions to open source projects

    Benefits:
    - Competitive salary
    - Remote work
    - Health insurance
    - Unlimited PTO
    """
