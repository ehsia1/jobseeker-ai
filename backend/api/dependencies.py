"""FastAPI dependencies for authentication and usage limits."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.models.subscription import SubscriptionTier, UsageActionType
from backend.services.subscription_service import (
    SubscriptionService,
    UsageLimitExceeded,
    FeatureNotAvailable,
)

logger = logging.getLogger(__name__)

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from JWT token (required)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, or None in demo mode."""
    if settings.demo_mode and token is None:
        return None

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


def get_subscription_service(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    """Get subscription service instance."""
    return SubscriptionService(db)


class UsageChecker:
    """Dependency factory for checking usage limits.

    Usage:
        @router.post("/proposals/generate")
        async def generate_proposal(
            ...,
            usage: Subscription = Depends(UsageChecker(UsageActionType.PROPOSAL_GENERATE))
        ):
            # Usage has been checked and recorded
            ...
    """

    def __init__(
        self,
        action: UsageActionType,
        record_usage: bool = True,
        required_feature: Optional[str] = None,
    ):
        self.action = action
        self.record_usage = record_usage
        self.required_feature = required_feature

    async def __call__(
        self,
        current_user: Optional[User] = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Check usage limits and optionally record usage."""
        # Skip usage limits entirely in demo mode
        if settings.demo_mode:
            return None

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for this action",
            )

        service = SubscriptionService(db)

        try:
            # Check feature access if required
            if self.required_feature:
                has_access = await service.check_feature_access(
                    current_user.id, self.required_feature
                )
                if not has_access:
                    subscription = await service.get_or_create_subscription(
                        current_user.id
                    )
                    raise FeatureNotAvailable(
                        self.required_feature, subscription.tier.value
                    )

            # Check and record usage
            if self.record_usage:
                subscription = await service.check_and_record_usage(
                    current_user.id, self.action
                )
            else:
                # Just check without recording
                subscription = await service.get_or_create_subscription(
                    current_user.id
                )

            return subscription

        except UsageLimitExceeded as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "usage_limit_exceeded",
                    "message": str(e),
                    "action": e.action,
                    "limit": e.limit,
                    "used": e.used,
                    "reset_date": e.reset_date.isoformat() if e.reset_date else None,
                    "upgrade_url": "/pricing",
                },
            )
        except FeatureNotAvailable as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "feature_not_available",
                    "message": str(e),
                    "feature": e.feature,
                    "current_tier": e.current_tier,
                    "required_tier": e.required_tier,
                    "upgrade_url": "/pricing",
                },
            )


class ToneChecker:
    """Dependency factory for checking proposal tone access.

    Usage:
        @router.post("/proposals/generate")
        async def generate_proposal(
            request: GenerateRequest,
            tone_access: bool = Depends(ToneChecker(lambda r: r.tone))
        ):
            ...
    """

    def __init__(self, tone_getter):
        """
        Args:
            tone_getter: Callable that extracts tone from request,
                        or a static tone string
        """
        self.tone_getter = tone_getter

    async def __call__(
        self,
        current_user: Optional[User] = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Check if user can use the requested tone."""
        # Skip in demo mode with no user
        if settings.demo_mode and current_user is None:
            return True

        if current_user is None:
            # For non-demo mode, require auth
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        return True  # Actual tone checking happens in UsageChecker or route


class FeatureGate:
    """Dependency factory for gating features by subscription tier.

    Usage:
        @router.post("/proposals/enhance")
        async def enhance_proposal(
            ...,
            _: None = Depends(FeatureGate("proposal_enhance"))
        ):
            ...
    """

    def __init__(self, feature: str):
        self.feature = feature

    async def __call__(
        self,
        current_user: Optional[User] = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Check if user has access to the feature."""
        # Skip feature gates entirely in demo mode (allow all features)
        if settings.demo_mode:
            return True

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for this feature",
            )

        service = SubscriptionService(db)

        try:
            has_access = await service.check_feature_access(
                current_user.id, self.feature
            )
            if not has_access:
                subscription = await service.get_or_create_subscription(
                    current_user.id
                )
                raise FeatureNotAvailable(self.feature, subscription.tier.value)
            return True

        except FeatureNotAvailable as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "feature_not_available",
                    "message": str(e),
                    "feature": e.feature,
                    "current_tier": e.current_tier,
                    "required_tier": e.required_tier,
                    "upgrade_url": "/pricing",
                },
            )


# Pre-configured usage checkers for common actions
require_proposal_generate = UsageChecker(UsageActionType.PROPOSAL_GENERATE)
require_proposal_enhance = UsageChecker(
    UsageActionType.PROPOSAL_ENHANCE, required_feature="proposal_enhance"
)
require_jd_parse = UsageChecker(UsageActionType.JD_PARSE)
require_resume_parse = UsageChecker(UsageActionType.RESUME_PARSE)
require_job_search = UsageChecker(UsageActionType.JOB_SEARCH)

# Feature gates
require_analytics = FeatureGate("analytics")
require_auto_apply = FeatureGate("auto_apply")
require_priority_support = FeatureGate("priority_support")
