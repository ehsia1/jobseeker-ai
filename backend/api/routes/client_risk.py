"""Client Risk API routes."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User
from backend.models.job import Job, JobMatch
from backend.api.deps import get_current_user_or_demo
from backend.services.client_risk_service import get_client_risk_service
from backend.api.schemas.client_risk import (
    ClientRiskResponse,
    ClientRiskBrief,
    CompanyRiskProfileResponse,
    AnalyzeJobRequest,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/job/{job_id}", response_model=ClientRiskResponse)
async def get_job_risk(
    job_id: UUID,
    analyze_if_missing: bool = True,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get risk assessment for a specific job.

    If no assessment exists and analyze_if_missing is True,
    a new analysis will be performed.
    """
    service = get_client_risk_service(db)

    # Check if job exists
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Get or create assessment
    assessment = await service.get_job_risk(job_id)

    if not assessment and analyze_if_missing:
        try:
            assessment = await service.analyze_job(job_id)
        except Exception as e:
            logger.error(f"Failed to analyze job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to analyze job risk"
            )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk assessment available for this job"
        )

    return assessment


@router.post("/analyze", response_model=ClientRiskResponse)
async def analyze_job(
    request: AnalyzeJobRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a job for client risk factors.

    Use force_refresh=True to re-analyze even if an assessment exists.
    """
    service = get_client_risk_service(db)

    try:
        assessment = await service.analyze_job(
            job_id=request.job_id,
            force_refresh=request.force_refresh
        )
        return assessment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job risk"
        )


@router.post("/analyze/batch", response_model=BatchAnalyzeResponse)
async def analyze_jobs_batch(
    request: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Analyze multiple jobs for risk (up to 10 at a time).

    Analysis is performed in the background for jobs that don't have assessments.
    """
    if len(request.job_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 jobs can be analyzed at once"
        )

    service = get_client_risk_service(db)

    results = []
    failed = 0

    for job_id in request.job_ids:
        try:
            assessment = await service.analyze_job(job_id)
            top_concern = None
            if assessment.red_flags:
                top_concern = assessment.red_flags[0].get("flag")

            results.append(ClientRiskBrief(
                job_id=assessment.job_id,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                top_concern=top_concern,
                analyzed_at=assessment.analyzed_at,
            ))
        except Exception as e:
            logger.error(f"Failed to analyze job {job_id}: {e}")
            failed += 1

    return BatchAnalyzeResponse(
        analyzed=len(results),
        failed=failed,
        results=results
    )


@router.get("/matches", response_model=List[ClientRiskBrief])
async def get_risk_for_matches(
    min_score: int = 0,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get risk assessments for all user's job matches.

    Returns brief risk info for each matched job that has been analyzed.
    """
    service = get_client_risk_service(db)

    # Get user's job matches
    matches_result = await db.execute(
        select(JobMatch)
        .where(JobMatch.user_id == current_user.id)
        .where(JobMatch.score >= min_score)
    )
    matches = matches_result.scalars().all()

    results = []
    for match in matches:
        assessment = await service.get_job_risk(match.job_id)
        if assessment:
            top_concern = None
            if assessment.red_flags:
                top_concern = assessment.red_flags[0].get("flag")

            results.append(ClientRiskBrief(
                job_id=assessment.job_id,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                top_concern=top_concern,
                analyzed_at=assessment.analyzed_at,
            ))

    return results


@router.get("/company/{company_name}", response_model=CompanyRiskProfileResponse)
async def get_company_risk_profile(
    company_name: str,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated risk profile for a company.

    Shows patterns across all jobs from this company.
    """
    service = get_client_risk_service(db)

    profile = await service.get_company_profile(company_name)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk profile found for this company"
        )

    return profile


@router.get("/companies", response_model=List[CompanyRiskProfileResponse])
async def list_company_profiles(
    risk_level: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """List company risk profiles.

    Optionally filter by risk level: low, medium, high, critical
    """
    from backend.models.client_risk import CompanyRiskProfile

    query = select(CompanyRiskProfile).order_by(
        CompanyRiskProfile.average_risk_score.desc()
    ).limit(limit)

    if risk_level:
        query = query.where(CompanyRiskProfile.risk_level == risk_level)

    result = await db.execute(query)
    profiles = result.scalars().all()

    return profiles


@router.get("/stats")
async def get_risk_stats(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get risk statistics across user's matches."""
    from backend.models.client_risk import ClientRiskAssessment
    from sqlalchemy import func

    # Get assessments for user's matches
    assessments_query = (
        select(ClientRiskAssessment)
        .join(JobMatch, JobMatch.job_id == ClientRiskAssessment.job_id)
        .where(JobMatch.user_id == current_user.id)
    )

    result = await db.execute(assessments_query)
    assessments = result.scalars().all()

    if not assessments:
        return {
            "total_analyzed": 0,
            "average_risk_score": 0,
            "risk_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "top_concerns": [],
        }

    # Calculate stats
    total = len(assessments)
    avg_score = sum(a.risk_score for a in assessments) / total

    distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for a in assessments:
        level = a.risk_level or "low"
        distribution[level] = distribution.get(level, 0) + 1

    # Aggregate top concerns
    concern_counts: dict = {}
    for a in assessments:
        for flag in (a.red_flags or []):
            text = flag.get("flag", "Unknown")
            concern_counts[text] = concern_counts.get(text, 0) + 1

    top_concerns = [
        {"concern": k, "count": v}
        for k, v in sorted(concern_counts.items(), key=lambda x: -x[1])[:5]
    ]

    return {
        "total_analyzed": total,
        "average_risk_score": round(avg_score, 1),
        "risk_distribution": distribution,
        "top_concerns": top_concerns,
    }
