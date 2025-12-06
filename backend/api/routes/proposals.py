"""Proposals routes for generating and enhancing job proposals."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.models.job import Job
from backend.models.subscription import Subscription
from backend.services.proposal_service import ProposalService, ProposalTone
from backend.services.jd_parser_service import ParsedJD
from backend.api.schemas.proposals import (
    GenerateProposalRequest,
    GenerateAllTonesRequest,
    EnhanceProposalRequest,
    ProposalResponse,
    AllTonesResponse,
    EnhanceProposalResponse,
    ParsedJDInput,
)
from backend.api.dependencies import (
    get_optional_current_user,
    require_proposal_generate,
    require_proposal_enhance,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_to_parsed_jd(parsed_input: ParsedJDInput) -> ParsedJD:
    """Convert API schema to service dataclass."""
    return ParsedJD(
        title=parsed_input.title,
        company=parsed_input.company,
        required_skills=parsed_input.required_skills,
        nice_to_have_skills=parsed_input.nice_to_have_skills,
        experience_level=parsed_input.experience_level,
        key_requirements=parsed_input.key_requirements,
        keywords_to_emphasize=parsed_input.keywords_to_emphasize,
        responsibilities=parsed_input.responsibilities,
        remote=parsed_input.remote,
        raw_text=parsed_input.raw_text,
    )


@router.post("/generate", response_model=ProposalResponse)
async def generate_proposal(
    request: GenerateProposalRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    subscription: Optional[Subscription] = Depends(require_proposal_generate),
    db: AsyncSession = Depends(get_db),
):
    """Generate a tailored proposal for a job.

    Provide either job_id (for a saved job) or parsed_jd (for pasted JD text).
    When authenticated, the proposal will be personalized to your profile.

    Usage limits apply based on subscription tier.
    """
    # Validate input
    if not request.job_id and not request.parsed_jd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either job_id or parsed_jd must be provided",
        )

    try:
        service = ProposalService(db=db)

        # Get job from database if job_id provided
        job = None
        if request.job_id:
            try:
                job_uuid = UUID(request.job_id)
                result = await db.execute(select(Job).where(Job.id == job_uuid))
                job = result.scalar_one_or_none()
                if job is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Job not found",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid job_id format",
                )

        # Convert parsed_jd if provided
        parsed_jd = None
        if request.parsed_jd:
            parsed_jd = _convert_to_parsed_jd(request.parsed_jd)

        # Get user profile if authenticated
        profile = None
        user_id = None
        if current_user:
            user_id = current_user.id
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == current_user.id)
            )
            profile = result.scalar_one_or_none()

        # Map tone enum
        tone = ProposalTone(request.tone.value)

        # Generate proposal
        proposal = await service.generate(
            job=job,
            parsed_jd=parsed_jd,
            profile=profile,
            user_id=user_id,
            tone=tone,
            additional_context=request.additional_context,
        )

        return ProposalResponse(
            content=proposal.content,
            tone=proposal.tone.value,
            word_count=proposal.word_count,
            keywords_used=proposal.keywords_used,
            experience_highlighted=proposal.experience_highlighted,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate proposal. Please try again.",
        )


@router.post("/generate-all", response_model=AllTonesResponse)
async def generate_all_tones(
    request: GenerateAllTonesRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    subscription: Optional[Subscription] = Depends(require_proposal_generate),
    db: AsyncSession = Depends(get_db),
):
    """Generate proposals in all three tones (short, medium, full).

    Useful for giving users options to choose from.
    Note: Counts as 1 proposal usage regardless of number of tones.
    """
    # Validate input
    if not request.job_id and not request.parsed_jd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either job_id or parsed_jd must be provided",
        )

    try:
        service = ProposalService(db=db)

        # Get job from database if job_id provided
        job = None
        if request.job_id:
            try:
                job_uuid = UUID(request.job_id)
                result = await db.execute(select(Job).where(Job.id == job_uuid))
                job = result.scalar_one_or_none()
                if job is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Job not found",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid job_id format",
                )

        # Convert parsed_jd if provided
        parsed_jd = None
        if request.parsed_jd:
            parsed_jd = _convert_to_parsed_jd(request.parsed_jd)

        # Get user profile if authenticated
        profile = None
        user_id = None
        if current_user:
            user_id = current_user.id
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == current_user.id)
            )
            profile = result.scalar_one_or_none()

        # Generate all tones
        proposals = await service.generate_all_tones(
            job=job,
            parsed_jd=parsed_jd,
            profile=profile,
            user_id=user_id,
            additional_context=request.additional_context,
        )

        return AllTonesResponse(
            short=ProposalResponse(
                content=proposals["short"].content,
                tone=proposals["short"].tone.value,
                word_count=proposals["short"].word_count,
                keywords_used=proposals["short"].keywords_used,
                experience_highlighted=proposals["short"].experience_highlighted,
            ),
            medium=ProposalResponse(
                content=proposals["medium"].content,
                tone=proposals["medium"].tone.value,
                word_count=proposals["medium"].word_count,
                keywords_used=proposals["medium"].keywords_used,
                experience_highlighted=proposals["medium"].experience_highlighted,
            ),
            full=ProposalResponse(
                content=proposals["full"].content,
                tone=proposals["full"].tone.value,
                word_count=proposals["full"].word_count,
                keywords_used=proposals["full"].keywords_used,
                experience_highlighted=proposals["full"].experience_highlighted,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate proposals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate proposals. Please try again.",
        )


@router.post("/enhance", response_model=EnhanceProposalResponse)
async def enhance_proposal(
    request: EnhanceProposalRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    subscription: Optional[Subscription] = Depends(require_proposal_enhance),
    db: AsyncSession = Depends(get_db),
):
    """Enhance an existing proposal draft.

    Available enhancements:
    - add_keywords: Naturally incorporate relevant keywords from the JD
    - improve_tone: Make more professional and engaging
    - add_metrics: Add quantified achievements where possible
    - shorten: Make more concise while keeping key points
    - expand: Add more detail and specific examples

    Requires Starter tier or higher.
    """
    try:
        service = ProposalService(db=db)

        # Get job from database if job_id provided
        job = None
        if request.job_id:
            try:
                job_uuid = UUID(request.job_id)
                result = await db.execute(select(Job).where(Job.id == job_uuid))
                job = result.scalar_one_or_none()
            except ValueError:
                pass  # Invalid UUID, just skip job lookup

        # Convert parsed_jd if provided
        parsed_jd = None
        if request.parsed_jd:
            parsed_jd = _convert_to_parsed_jd(request.parsed_jd)

        # Get user profile if authenticated
        profile = None
        if current_user:
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == current_user.id)
            )
            profile = result.scalar_one_or_none()

        # Convert enhancement types to strings
        enhancements = [e.value for e in request.enhancements]

        # Enhance proposal
        enhanced = await service.enhance(
            original_proposal=request.original_proposal,
            job=job,
            parsed_jd=parsed_jd,
            profile=profile,
            enhancements=enhancements,
        )

        return EnhanceProposalResponse(
            enhanced_proposal=enhanced.content,
            tone=enhanced.tone.value,
            word_count=enhanced.word_count,
            keywords_used=enhanced.keywords_used,
            enhancements_applied=enhancements,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to enhance proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enhance proposal. Please try again.",
        )


@router.get("/health")
async def proposals_health():
    """Check if the proposal service is operational."""
    from backend.services.llm_service import get_llm_service

    llm = get_llm_service()
    is_available = llm.is_available()

    return {
        "status": "healthy" if is_available else "degraded",
        "llm_provider": llm.provider,
        "llm_model": llm.model,
        "llm_available": is_available,
        "demo_mode": settings.demo_mode,
        "available_tones": ["short", "medium", "full"],
        "available_enhancements": [
            "add_keywords",
            "improve_tone",
            "add_metrics",
            "shorten",
            "expand",
        ],
    }
