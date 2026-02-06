"""A/B Testing API routes."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.api.deps import get_current_user_or_demo
from backend.services.ab_test_service import get_ab_test_service
from backend.services.proposal_service import ProposalService, ProposalTone
from backend.api.schemas.ab_test import (
    ABTestCreate,
    ABTestResponse,
    ABTestWithVariants,
    ABTestUpdate,
    ProposalVariantCreate,
    ProposalVariantResponse,
    ProposalVariantUpdate,
    RecordOutcomeRequest,
    VariantStatsResponse,
    GenerateABVariantsRequest,
    GenerateABVariantsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============= A/B Test Endpoints =============


@router.post("/tests", response_model=ABTestResponse, status_code=status.HTTP_201_CREATED)
async def create_ab_test(
    request: ABTestCreate,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Create a new A/B test.

    A/B tests allow you to compare different proposal approaches
    and track which performs better in terms of response rates.
    """
    service = get_ab_test_service(db)

    ab_test = await service.create_ab_test(
        user_id=current_user.id,
        name=request.name,
        test_type=request.test_type,
        description=request.description,
        parameters=request.parameters,
        target_sample_size=request.target_sample_size,
    )

    return ab_test


@router.get("/tests", response_model=List[ABTestResponse])
async def list_ab_tests(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """List all A/B tests for the current user.

    Optionally filter by status: draft, active, paused, completed.
    """
    service = get_ab_test_service(db)
    tests = await service.get_user_ab_tests(
        user_id=current_user.id,
        status=status_filter,
    )
    return tests


@router.get("/tests/{test_id}", response_model=ABTestWithVariants)
async def get_ab_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get an A/B test by ID with all associated variants."""
    service = get_ab_test_service(db)
    ab_test = await service.get_ab_test(test_id, current_user.id)

    if not ab_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A/B test not found",
        )

    return ab_test


@router.post("/tests/{test_id}/start", response_model=ABTestResponse)
async def start_ab_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Start an A/B test.

    Changes status from 'draft' to 'active' and records start time.
    """
    service = get_ab_test_service(db)

    try:
        ab_test = await service.start_ab_test(test_id, current_user.id)
        return ab_test
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/tests/{test_id}/pause", response_model=ABTestResponse)
async def pause_ab_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active A/B test."""
    service = get_ab_test_service(db)

    try:
        ab_test = await service.pause_ab_test(test_id, current_user.id)
        return ab_test
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/tests/{test_id}/complete", response_model=ABTestResponse)
async def complete_ab_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Complete an A/B test and calculate results.

    Analyzes all variants and determines the winner based on
    response rates and other metrics.
    """
    service = get_ab_test_service(db)

    try:
        ab_test = await service.complete_ab_test(test_id, current_user.id)
        return ab_test
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ab_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Delete an A/B test and all associated variants."""
    service = get_ab_test_service(db)
    deleted = await service.delete_ab_test(test_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A/B test not found",
        )


# ============= Variant Endpoints =============


@router.post("/variants", response_model=ProposalVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant(
    request: ProposalVariantCreate,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Create a new proposal variant.

    Variants can be standalone or associated with a job match
    and/or an A/B test.
    """
    service = get_ab_test_service(db)

    variant = await service.create_variant(
        user_id=current_user.id,
        content=request.content,
        job_match_id=request.job_match_id,
        ab_test_id=request.ab_test_id,
        variant_name=request.variant_name,
        variant_label=request.variant_label,
        tone=request.tone,
        style=request.style,
        length=request.length,
        generation_method=request.generation_method,
        model_used=request.model_used,
        keywords_used=request.keywords_used,
        ats_score=request.ats_score,
        is_control=request.is_control,
    )

    return variant


@router.get("/variants", response_model=List[ProposalVariantResponse])
async def list_variants(
    job_match_id: Optional[UUID] = None,
    ab_test_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """List variants for a job match or A/B test."""
    service = get_ab_test_service(db)

    if job_match_id:
        variants = await service.get_variants_for_job(job_match_id, current_user.id)
    elif ab_test_id:
        variants = await service.get_variants_for_test(ab_test_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either job_match_id or ab_test_id is required",
        )

    return variants


@router.get("/variants/{variant_id}", response_model=ProposalVariantResponse)
async def get_variant(
    variant_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get a variant by ID."""
    service = get_ab_test_service(db)
    variant = await service.get_variant(variant_id, current_user.id)

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    return variant


@router.post("/variants/{variant_id}/select", response_model=ProposalVariantResponse)
async def select_variant(
    variant_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Mark a variant as selected (the one to use).

    This unselects any other variants for the same job match.
    """
    service = get_ab_test_service(db)

    try:
        variant = await service.select_variant(variant_id, current_user.id)
        return variant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/variants/{variant_id}/send", response_model=ProposalVariantResponse)
async def mark_variant_sent(
    variant_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Mark a variant as sent.

    Records the send timestamp for tracking response times.
    """
    service = get_ab_test_service(db)

    try:
        variant = await service.mark_variant_sent(variant_id, current_user.id)
        return variant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/variants/{variant_id}/outcome", response_model=ProposalVariantResponse)
async def record_variant_outcome(
    variant_id: UUID,
    request: RecordOutcomeRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Record an outcome for a variant.

    Valid outcome types: response, interview, offer.
    """
    service = get_ab_test_service(db)

    try:
        variant = await service.record_outcome(
            variant_id,
            current_user.id,
            request.outcome_type,
        )
        return variant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    variant_id: UUID,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Delete a variant."""
    service = get_ab_test_service(db)
    deleted = await service.delete_variant(variant_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )


# ============= Analytics Endpoints =============


@router.get("/stats", response_model=VariantStatsResponse)
async def get_variant_stats(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated variant statistics for the current user.

    Includes overall metrics and breakdowns by tone and style.
    """
    service = get_ab_test_service(db)
    stats = await service.get_user_variant_stats(current_user.id)
    return stats


# ============= Quick Generate Endpoints =============


@router.post("/generate-ab", response_model=GenerateABVariantsResponse)
async def generate_ab_variants(
    request: GenerateABVariantsRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Generate A/B test variants for a job.

    Creates two proposal variants with different configurations
    (e.g., formal vs casual tone) and optionally links them to
    an existing A/B test.
    """
    ab_service = get_ab_test_service(db)
    proposal_service = ProposalService(db)

    # Get the job match
    from backend.models.job import JobMatch
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(JobMatch)
        .options(selectinload(JobMatch.job))
        .where(
            JobMatch.id == request.job_match_id,
            JobMatch.user_id == current_user.id,
        )
    )
    job_match = result.scalar_one_or_none()

    if not job_match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found",
        )

    # Get user profile
    from backend.models.user import UserProfile

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found. Please complete your profile first.",
        )

    # Generate variant A
    tone_a = request.variant_a_config.get("tone", "medium")
    try:
        tone_enum_a = ProposalTone(tone_a)
    except ValueError:
        tone_enum_a = ProposalTone.MEDIUM

    proposal_a = await proposal_service.generate_proposal(
        job=job_match.job,
        profile=profile,
        user_id=current_user.id,
        tone=tone_enum_a,
    )

    variant_a = await ab_service.create_variant(
        user_id=current_user.id,
        content=proposal_a.content,
        job_match_id=request.job_match_id,
        ab_test_id=request.ab_test_id,
        variant_name=f"Variant A - {tone_a.title()}",
        variant_label="A",
        tone=tone_a,
        generation_method="proposal_service",
        model_used=proposal_a.metadata.get("model", "unknown"),
        keywords_used=proposal_a.keywords_used,
        is_control=True,
    )

    # Generate variant B
    tone_b = request.variant_b_config.get("tone", "full")
    try:
        tone_enum_b = ProposalTone(tone_b)
    except ValueError:
        tone_enum_b = ProposalTone.FULL

    proposal_b = await proposal_service.generate_proposal(
        job=job_match.job,
        profile=profile,
        user_id=current_user.id,
        tone=tone_enum_b,
    )

    variant_b = await ab_service.create_variant(
        user_id=current_user.id,
        content=proposal_b.content,
        job_match_id=request.job_match_id,
        ab_test_id=request.ab_test_id,
        variant_name=f"Variant B - {tone_b.title()}",
        variant_label="B",
        tone=tone_b,
        generation_method="proposal_service",
        model_used=proposal_b.metadata.get("model", "unknown"),
        keywords_used=proposal_b.keywords_used,
        is_control=False,
    )

    return GenerateABVariantsResponse(
        variant_a=variant_a,
        variant_b=variant_b,
        ab_test_id=request.ab_test_id,
    )
