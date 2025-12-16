"""Job management routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.models.job import Job
from backend.api.schemas.job import (
    JobRead, JobSummary, JobSearch,
    ScoredJobSummary, ScoredSearchResponse, ScoreBreakdownSchema
)
from backend.api.routes.auth import get_current_user
from backend.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[JobSummary])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    remote_only: bool = Query(False),
    min_rate: float = Query(None, ge=0),
    max_rate: float = Query(None, ge=0),
    source: str = Query(None),
    location: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List jobs with filtering."""

    query = select(Job).order_by(desc(Job.posted_at))

    # Apply filters
    filters = []

    if remote_only:
        filters.append(Job.remote == True)

    if min_rate is not None:
        filters.append(
            or_(
                Job.rate_min >= min_rate,
                Job.rate_max >= min_rate
            )
        )

    if max_rate is not None:
        filters.append(
            or_(
                Job.rate_max <= max_rate,
                Job.rate_min <= max_rate
            )
        )

    if source:
        filters.append(Job.source == source)

    if location:
        # Case-insensitive location search
        filters.append(Job.location.ilike(f"%{location}%"))
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return jobs


@router.get("/{job_id}/", response_model=JobRead)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get job details by ID."""
    from uuid import UUID

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    result = await db.execute(
        select(Job).where(Job.id == job_uuid)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.post("/search/", response_model=ScoredSearchResponse)
async def search_jobs(
    search_params: JobSearch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search jobs with advanced parameters and return scored results."""

    query = select(Job).order_by(desc(Job.posted_at))

    filters = []

    # Text search in title and description
    search_text = search_params.query
    if not search_text and search_params.keywords:
        search_text = " ".join(search_params.keywords)

    if search_text:
        search_term = f"%{search_text.lower()}%"
        filters.append(
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term),
                Job.company.ilike(search_term)
            )
        )

    # Skills filtering
    if search_params.skills:
        # Use JSONB contains for skills array
        for skill in search_params.skills:
            filters.append(Job.skills.contains([skill]))

    # Location filtering
    if search_params.location:
        location_term = f"%{search_params.location.lower()}%"
        filters.append(Job.location.ilike(location_term))

    # Remote only
    if search_params.remote_only:
        filters.append(Job.remote == True)

    # Rate filtering
    if search_params.min_rate:
        filters.append(
            or_(
                Job.rate_min >= search_params.min_rate,
                Job.rate_max >= search_params.min_rate
            )
        )

    if search_params.max_rate:
        filters.append(
            or_(
                Job.rate_min <= search_params.max_rate,
                Job.rate_max <= search_params.max_rate
            )
        )

    # Rate type filtering
    if search_params.rate_type:
        filters.append(Job.rate_type == search_params.rate_type)

    # Source filtering
    if search_params.sources:
        filters.append(Job.source.in_(search_params.sources))

    # Posted date filtering
    if search_params.posted_after:
        filters.append(Job.posted_at >= search_params.posted_after)

    if filters:
        query = query.where(and_(*filters))

    query = query.limit(search_params.limit).offset(search_params.offset)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Get user's profile for scoring
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    # Score each job
    scoring_service = ScoringService()
    scored_jobs = []
    source_stats = {}

    for job in jobs:
        # Track source stats
        source_name = job.source or "unknown"
        source_stats[source_name] = source_stats.get(source_name, 0) + 1

        # Score the job against user profile
        if profile:
            try:
                score_result = scoring_service.score_job(job, profile)
                explanation = scoring_service.generate_explanation(job, profile, score_result)

                score_breakdown = ScoreBreakdownSchema(
                    skill_match=score_result.skill_match,
                    experience_match=score_result.experience_match,
                    compensation_match=score_result.compensation_match,
                    location_match=score_result.location_match,
                    semantic_similarity=score_result.semantic_similarity,
                    freshness_score=score_result.freshness_score,
                    preference_match=score_result.preference_match,
                )
                total_score = score_result.total_score
            except Exception as e:
                logger.warning(f"Error scoring job {job.id}: {e}")
                score_breakdown = ScoreBreakdownSchema(
                    skill_match=50, experience_match=50,
                    compensation_match=50, location_match=50
                )
                total_score = 50
                explanation = "Unable to calculate match score"
        else:
            # No profile, use neutral scores
            score_breakdown = ScoreBreakdownSchema(
                skill_match=50, experience_match=50,
                compensation_match=50, location_match=50
            )
            total_score = 50
            explanation = "Complete your profile for personalized matching"

        scored_job = ScoredJobSummary(
            id=job.id,
            title=job.title,
            company=job.company,
            description=job.description[:500] if job.description else None,
            location=job.location,
            remote=job.remote,
            rate_min=job.rate_min,
            rate_max=job.rate_max,
            rate_type=job.rate_type,
            employment_type=job.duration,  # Map duration to employment_type
            skills=job.skills or [],
            posted_at=job.posted_at,
            url=job.url,
            source=job.source,
            total_score=total_score,
            score_breakdown=score_breakdown,
            explanation=explanation,
            recommended=total_score >= 70,
        )
        scored_jobs.append(scored_job)

    # Sort by score (highest first)
    scored_jobs.sort(key=lambda x: x.total_score, reverse=True)

    return ScoredSearchResponse(
        success=True,
        total_results=len(scored_jobs),
        source_stats=source_stats,
        jobs=scored_jobs,
    )


@router.get("/sources/list/")
async def list_job_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List available job sources."""
    
    result = await db.execute(
        select(Job.source).distinct()
    )
    sources = [row[0] for row in result.all()]
    
    return {"sources": sources}


@router.get("/professions/list/")
async def list_professions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List available professions for job search."""
    from backend.searchers.searcher_registry import SearcherRegistry
    
    professions = SearcherRegistry.get_all_professions()
    
    # Format professions nicely
    formatted = []
    for prof in professions:
        formatted.append({
            "value": prof,
            "label": prof.replace("_", " ").title(),
            "searcher_count": len(SearcherRegistry.PROFESSION_SEARCHERS[prof])
        })
    
    return {
        "professions": formatted,
        "total": len(formatted)
    }


@router.post("/search/live/")
async def search_live_jobs(
    search_params: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for jobs across live job boards."""
    from backend.services.job_search_service import JobSearchService
    
    service = JobSearchService(db)
    
    keywords = search_params.get("keywords", [])
    profession = search_params.get("profession")
    remote_only = search_params.get("remote_only", True)
    limit = search_params.get("limit", 10)
    
    results = await service.search_by_keywords(
        keywords=keywords,
        profession=profession,
        remote_only=remote_only,
        limit_per_source=limit
    )
    
    return results


@router.post("/search/profile/")
async def search_jobs_for_profile(
    search_params: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for jobs based on user's profile."""
    from backend.services.job_search_service import JobSearchService
    from backend.models.user import UserProfile
    
    service = JobSearchService(db)
    
    # Get user's profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found. Please complete your profile first."
        )
    
    custom_keywords = search_params.get("keywords")
    limit = search_params.get("limit", 10)
    
    results = await service.search_for_user(
        user=current_user,
        custom_keywords=custom_keywords,
        limit_per_source=limit
    )
    
    return results