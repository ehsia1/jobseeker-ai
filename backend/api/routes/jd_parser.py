"""JD Parser routes for analyzing job descriptions."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.models.user import User, UserProfile
from backend.models.subscription import Subscription
from backend.services.jd_parser_service import JDParserService
from backend.api.schemas.jd_parser import (
    ParseJDRequest,
    JDParseResponse,
    ParsedJDResponse,
    ScoreBreakdownResponse,
    ExtractKeywordsRequest,
    ExtractKeywordsResponse,
)
from backend.api.dependencies import (
    get_optional_current_user,
    require_jd_parse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/parse", response_model=JDParseResponse)
async def parse_job_description(
    request: ParseJDRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    subscription: Optional[Subscription] = Depends(require_jd_parse),
    db: AsyncSession = Depends(get_db),
):
    """Parse a job description and optionally score against user profile.

    In demo mode, works without authentication (no scoring).
    When authenticated, includes match score against user's profile.

    Usage limits apply based on subscription tier.
    """
    try:
        service = JDParserService(db=db)

        # Get user profile if authenticated
        profile = None
        user_id = None

        if current_user:
            user_id = current_user.id
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == current_user.id)
            )
            profile = result.scalar_one_or_none()

        # Parse and optionally score
        if profile:
            parse_result = await service.parse_and_score(
                jd_text=request.text,
                user_id=user_id,
                profile=profile,
            )

            return JDParseResponse(
                parsed=ParsedJDResponse(**parse_result.parsed.to_dict()),
                match_score=ScoreBreakdownResponse(
                    **parse_result.match_score.to_dict()
                )
                if parse_result.match_score
                else None,
                explanation=parse_result.explanation,
            )
        else:
            # Just parse without scoring
            parsed = await service.parse(request.text)

            return JDParseResponse(
                parsed=ParsedJDResponse(**parsed.to_dict()),
                match_score=None,
                explanation="Log in to see how well this job matches your profile."
                if not settings.demo_mode
                else "Demo mode: Create a profile to see match scores.",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to parse JD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job description. Please try again.",
        )


@router.post("/keywords", response_model=ExtractKeywordsResponse)
async def extract_keywords(
    request: ExtractKeywordsRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract important keywords from a job description.

    These keywords are useful for tailoring proposals and resumes.
    """
    try:
        service = JDParserService(db=db)
        keywords = await service.extract_keywords(request.text)

        return ExtractKeywordsResponse(keywords=keywords)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to extract keywords: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract keywords. Please try again.",
        )


@router.get("/health")
async def jd_parser_health():
    """Check if the JD parser service is operational."""
    from backend.services.llm_service import get_llm_service

    llm = get_llm_service()
    is_available = llm.is_available()

    return {
        "status": "healthy" if is_available else "degraded",
        "llm_provider": llm.provider,
        "llm_model": llm.model,
        "llm_available": is_available,
        "demo_mode": settings.demo_mode,
    }
