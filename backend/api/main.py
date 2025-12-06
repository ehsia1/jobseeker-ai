"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from backend.config import settings
from backend.database import init_db, close_db
from backend.api.routes import auth, users, jobs, matches, feedback, health, ingestion, matching, jd_parser, proposals, resume, subscription


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    if SENTRY_AVAILABLE and settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                FastApiIntegration(auto_enable=True),
                SqlalchemyIntegration(),
            ],
            environment=settings.environment,
            traces_sample_rate=0.1,
        )
    
    await init_db()
    print(f"🚀 {settings.app_name} started in {settings.environment} mode")
    
    yield
    
    # Shutdown
    await close_db()
    print("👋 Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered job discovery and application assistant",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with actual domains in production
    )

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(matches.router, prefix="/matches", tags=["Matches"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
app.include_router(matching.router, prefix="/matching", tags=["Matching"])
app.include_router(jd_parser.router, prefix="/jd", tags=["JD Parser"])
app.include_router(proposals.router, prefix="/proposals", tags=["Proposals"])
app.include_router(resume.router, prefix="/resume", tags=["Resume"])
app.include_router(subscription.router, prefix="/subscription", tags=["Subscription"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "disabled",
    }