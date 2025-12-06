"""Subscription management routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.models.subscription import SubscriptionTier, TIER_LIMITS
from backend.services.subscription_service import SubscriptionService
from backend.api.dependencies import get_current_user, get_optional_current_user
from backend.api.schemas.subscription import (
    SubscriptionTierEnum,
    TierFeatures,
    TierLimits,
    TierInfo,
    SubscriptionRead,
    SubscriptionWithUsage,
    UsageStats,
    CreateCheckoutRequest,
    CreateCheckoutResponse,
    CreatePortalRequest,
    CreatePortalResponse,
    CancelRequest,
    SubscriptionActionResponse,
    PricingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _tier_to_enum(tier: SubscriptionTier) -> SubscriptionTierEnum:
    """Convert database tier to API enum."""
    return SubscriptionTierEnum(tier.value)


def _get_tier_features(tier: SubscriptionTier) -> TierFeatures:
    """Get features for a tier."""
    limits = TIER_LIMITS[tier]
    return TierFeatures(
        proposal_tones=limits["proposal_tones"],
        proposal_enhance=limits["proposal_enhance"],
        auto_apply=limits["auto_apply"],
        priority_support=limits["priority_support"],
        analytics=limits["analytics"],
    )


def _get_tier_limits(tier: SubscriptionTier) -> TierLimits:
    """Get limits for a tier."""
    limits = TIER_LIMITS[tier]
    return TierLimits(
        proposals_per_month=limits["proposals_per_month"],
        jd_parses_per_month=limits["jd_parses_per_month"],
        job_searches_per_day=limits["job_searches_per_day"],
        resume_uploads=limits["resume_uploads"],
        features=_get_tier_features(tier),
    )


def _build_tier_info() -> list[TierInfo]:
    """Build tier info for pricing page."""
    tier_prices = {
        SubscriptionTier.FREE: (0, "Free"),
        SubscriptionTier.STARTER: (999, "$9.99/mo"),
        SubscriptionTier.PRO: (2499, "$24.99/mo"),
        SubscriptionTier.POWER: (4999, "$49.99/mo"),
    }

    popular_tier = SubscriptionTier.PRO

    tiers = []
    for tier in SubscriptionTier:
        price_cents, price_display = tier_prices[tier]
        tiers.append(TierInfo(
            id=_tier_to_enum(tier),
            name=tier.value.title(),
            price_cents=price_cents,
            price_display=price_display,
            limits=_get_tier_limits(tier),
            popular=(tier == popular_tier),
        ))

    return tiers


@router.get("/", response_model=SubscriptionWithUsage)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription with usage info."""
    service = SubscriptionService(db)
    subscription = await service.get_or_create_subscription(current_user.id)

    # Calculate remaining usage
    limits = TIER_LIMITS[subscription.tier]

    proposals_remaining = -1
    if limits["proposals_per_month"] != -1:
        proposals_remaining = max(0, limits["proposals_per_month"] - subscription.proposal_count)

    jd_parses_remaining = -1
    if limits["jd_parses_per_month"] != -1:
        jd_parses_remaining = max(0, limits["jd_parses_per_month"] - subscription.jd_parse_count)

    searches_remaining = -1
    if limits["job_searches_per_day"] != -1:
        searches_remaining = max(0, limits["job_searches_per_day"] - subscription.job_search_count_today)

    return SubscriptionWithUsage(
        id=subscription.id,
        user_id=subscription.user_id,
        tier=_tier_to_enum(subscription.tier),
        has_stripe_customer=bool(subscription.stripe_customer_id),
        has_active_subscription=bool(subscription.stripe_subscription_id),
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        canceled_at=subscription.canceled_at,
        proposal_count=subscription.proposal_count,
        jd_parse_count=subscription.jd_parse_count,
        job_search_count_today=subscription.job_search_count_today,
        usage_reset_date=subscription.usage_reset_date,
        daily_reset_date=subscription.daily_reset_date,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        proposals_remaining=proposals_remaining,
        jd_parses_remaining=jd_parses_remaining,
        searches_remaining_today=searches_remaining,
        tier_limits=_get_tier_limits(subscription.tier),
        is_active=True,
    )


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage statistics."""
    service = SubscriptionService(db)
    subscription = await service.get_or_create_subscription(current_user.id)

    limits = TIER_LIMITS[subscription.tier]

    # Calculate remaining
    proposals_limit = limits["proposals_per_month"]
    proposals_remaining = -1 if proposals_limit == -1 else max(0, proposals_limit - subscription.proposal_count)

    jd_limit = limits["jd_parses_per_month"]
    jd_remaining = -1 if jd_limit == -1 else max(0, jd_limit - subscription.jd_parse_count)

    search_limit = limits["job_searches_per_day"]
    search_remaining = -1 if search_limit == -1 else max(0, search_limit - subscription.job_search_count_today)

    return UsageStats(
        tier=_tier_to_enum(subscription.tier),
        is_active=True,
        proposals_used=subscription.proposal_count,
        proposals_limit=proposals_limit,
        proposals_remaining=proposals_remaining,
        jd_parses_used=subscription.jd_parse_count,
        jd_parses_limit=jd_limit,
        jd_parses_remaining=jd_remaining,
        job_searches_used_today=subscription.job_search_count_today,
        job_searches_limit_daily=search_limit,
        job_searches_remaining_today=search_remaining,
        monthly_reset_date=subscription.usage_reset_date,
        daily_reset_date=subscription.daily_reset_date,
        features=_get_tier_features(subscription.tier),
    )


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pricing page data."""
    current_tier = None

    if current_user:
        service = SubscriptionService(db)
        subscription = await service.get_or_create_subscription(current_user.id)
        current_tier = _tier_to_enum(subscription.tier)

    return PricingResponse(
        tiers=_build_tier_info(),
        current_tier=current_tier,
        stripe_publishable_key=settings.stripe_publishable_key if settings.stripe_configured else None,
    )


@router.post("/checkout", response_model=CreateCheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for subscription upgrade."""
    if not settings.stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    # Validate tier
    if request.tier == SubscriptionTierEnum.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout for free tier",
        )

    # Get price ID for tier
    price_mapping = {
        SubscriptionTierEnum.STARTER: settings.stripe_price_starter,
        SubscriptionTierEnum.PRO: settings.stripe_price_pro,
        SubscriptionTierEnum.POWER: settings.stripe_price_power,
    }

    price_id = price_mapping.get(request.tier)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Price not configured for tier: {request.tier.value}",
        )

    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        service = SubscriptionService(db)
        subscription = await service.get_or_create_subscription(current_user.id)

        # Get or create Stripe customer
        customer_id = subscription.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={"user_id": str(current_user.id)},
            )
            customer_id = customer.id

            # Update subscription with customer ID
            subscription.stripe_customer_id = customer_id
            await db.commit()

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "tier": request.tier.value,
            },
        )

        return CreateCheckoutResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id,
        )

    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post("/portal", response_model=CreatePortalResponse)
async def create_portal_session(
    request: CreatePortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe customer portal session for managing subscription."""
    if not settings.stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    service = SubscriptionService(db)
    subscription = await service.get_or_create_subscription(current_user.id)

    if not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to manage",
        )

    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=request.return_url,
        )

        return CreatePortalResponse(portal_url=portal_session.url)

    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session",
        )


@router.post("/cancel", response_model=SubscriptionActionResponse)
async def cancel_subscription(
    request: CancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current subscription."""
    if not settings.stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    service = SubscriptionService(db)
    subscription = await service.get_or_create_subscription(current_user.id)

    if not subscription.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel",
        )

    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        if request.at_period_end:
            # Cancel at end of period
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            message = "Subscription will be cancelled at the end of the billing period"
        else:
            # Cancel immediately
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            message = "Subscription cancelled immediately"

        # Update local record
        from datetime import datetime
        subscription.cancel_at_period_end = request.at_period_end
        subscription.canceled_at = datetime.utcnow()
        await db.commit()
        await db.refresh(subscription)

        return SubscriptionActionResponse(
            success=True,
            message=message,
            subscription=SubscriptionRead(
                id=subscription.id,
                user_id=subscription.user_id,
                tier=_tier_to_enum(subscription.tier),
                has_stripe_customer=bool(subscription.stripe_customer_id),
                has_active_subscription=bool(subscription.stripe_subscription_id),
                current_period_start=subscription.current_period_start,
                current_period_end=subscription.current_period_end,
                cancel_at_period_end=subscription.cancel_at_period_end,
                canceled_at=subscription.canceled_at,
                proposal_count=subscription.proposal_count,
                jd_parse_count=subscription.jd_parse_count,
                job_search_count_today=subscription.job_search_count_today,
                usage_reset_date=subscription.usage_reset_date,
                daily_reset_date=subscription.daily_reset_date,
                created_at=subscription.created_at,
                updated_at=subscription.updated_at,
            ),
        )

    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    if not settings.stripe_configured or not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key

        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    service = SubscriptionService(db)

    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_checkout_completed(session, service, db)

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        await _handle_subscription_updated(subscription, service, db)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await _handle_subscription_deleted(subscription, service, db)

    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        await _handle_payment_succeeded(invoice, service, db)

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await _handle_payment_failed(invoice, service, db)

    return {"status": "success"}


async def _handle_checkout_completed(session: dict, service: SubscriptionService, db: AsyncSession):
    """Handle successful checkout."""
    from uuid import UUID
    from datetime import datetime
    from sqlalchemy import select
    from backend.models.subscription import Subscription

    user_id = session.get("metadata", {}).get("user_id")
    tier_str = session.get("metadata", {}).get("tier")

    if not user_id or not tier_str:
        logger.warning("Checkout session missing metadata")
        return

    try:
        user_uuid = UUID(user_id)
        tier = SubscriptionTier(tier_str)
    except (ValueError, KeyError):
        logger.warning(f"Invalid metadata: user_id={user_id}, tier={tier_str}")
        return

    # Get subscription
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_uuid)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.tier = tier
        subscription.stripe_subscription_id = session.get("subscription")
        subscription.current_period_start = datetime.utcnow()
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        await db.commit()
        logger.info(f"Upgraded user {user_id} to {tier.value}")


async def _handle_subscription_updated(stripe_sub: dict, service: SubscriptionService, db: AsyncSession):
    """Handle subscription update."""
    from datetime import datetime
    from sqlalchemy import select
    from backend.models.subscription import Subscription

    stripe_sub_id = stripe_sub.get("id")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)

        if stripe_sub.get("current_period_end"):
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub["current_period_end"]
            )

        await db.commit()
        logger.info(f"Updated subscription {stripe_sub_id}")


async def _handle_subscription_deleted(stripe_sub: dict, service: SubscriptionService, db: AsyncSession):
    """Handle subscription cancellation."""
    from datetime import datetime
    from sqlalchemy import select
    from backend.models.subscription import Subscription

    stripe_sub_id = stripe_sub.get("id")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.tier = SubscriptionTier.FREE
        subscription.stripe_subscription_id = None
        subscription.current_period_end = None
        subscription.canceled_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Cancelled subscription {stripe_sub_id}")


async def _handle_payment_succeeded(invoice: dict, service: SubscriptionService, db: AsyncSession):
    """Handle successful payment - reset usage counters."""
    from datetime import datetime, date
    from sqlalchemy import select
    from backend.models.subscription import Subscription

    customer_id = invoice.get("customer")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        # Reset monthly counters on successful payment
        subscription.proposal_count = 0
        subscription.jd_parse_count = 0
        subscription.usage_reset_date = date.today()
        subscription.current_period_start = datetime.utcnow()
        await db.commit()
        logger.info(f"Reset usage for customer {customer_id}")


async def _handle_payment_failed(invoice: dict, service: SubscriptionService, db: AsyncSession):
    """Handle failed payment."""
    customer_id = invoice.get("customer")
    logger.warning(f"Payment failed for customer {customer_id}")
    # Could send email notification, flag account, etc.
