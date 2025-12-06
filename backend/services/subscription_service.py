"""Subscription and usage tracking service."""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.models.subscription import (
    Subscription,
    UsageLog,
    SubscriptionTier,
    UsageActionType,
    TIER_LIMITS,
    TIER_PRICING,
)
from backend.models.user import User

logger = logging.getLogger(__name__)


class UsageLimitExceeded(Exception):
    """Raised when a usage limit is exceeded."""

    def __init__(self, action: str, limit: int, used: int, reset_date: Optional[date] = None):
        self.action = action
        self.limit = limit
        self.used = used
        self.reset_date = reset_date
        super().__init__(
            f"Usage limit exceeded for {action}: {used}/{limit}. "
            f"Resets on {reset_date}" if reset_date else f"Usage limit exceeded for {action}"
        )


class FeatureNotAvailable(Exception):
    """Raised when a feature is not available in the user's tier."""

    def __init__(self, feature: str, current_tier: str, required_tier: str = "starter"):
        self.feature = feature
        self.current_tier = current_tier
        self.required_tier = required_tier
        super().__init__(
            f"Feature '{feature}' not available on {current_tier} tier. "
            f"Upgrade to {required_tier} or higher."
        )


class SubscriptionService:
    """Service for managing subscriptions and tracking usage."""

    def __init__(self, db: AsyncSession):
        """Initialize subscription service.

        Args:
            db: Database session.
        """
        self.db = db

    async def get_or_create_subscription(self, user_id: UUID) -> Subscription:
        """Get existing subscription or create a free one.

        Args:
            user_id: User ID.

        Returns:
            Subscription model.
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription is None:
            subscription = Subscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
                usage_reset_date=self._get_next_month_reset(),
                daily_reset_date=date.today(),
            )
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
            logger.info(f"Created free subscription for user {user_id}")

        return subscription

    async def get_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """Get subscription for a user.

        Args:
            user_id: User ID.

        Returns:
            Subscription or None.
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription_with_user(self, user_id: UUID) -> Optional[Subscription]:
        """Get subscription with user relationship loaded.

        Args:
            user_id: User ID.

        Returns:
            Subscription with user loaded.
        """
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .options(selectinload(Subscription.user))
        )
        return result.scalar_one_or_none()

    async def check_and_record_usage(
        self,
        user_id: UUID,
        action: UsageActionType,
        metadata: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None,
        cost_cents: Optional[int] = None,
    ) -> Subscription:
        """Check usage limits and record the action.

        Args:
            user_id: User ID.
            action: Type of action being performed.
            metadata: Additional context for the action.
            tokens_used: LLM tokens consumed (for analytics).
            cost_cents: Estimated cost in cents (for analytics).

        Returns:
            Updated subscription.

        Raises:
            UsageLimitExceeded: If the user has exceeded their limit.
        """
        subscription = await self.get_or_create_subscription(user_id)

        # Reset counters if needed
        subscription = await self._reset_counters_if_needed(subscription)

        # Check limits
        await self._check_limit(subscription, action)

        # Increment counter
        await self._increment_counter(subscription, action)

        # Log the usage
        usage_log = UsageLog(
            subscription_id=subscription.id,
            action_type=action,
            metadata=metadata or {},
            tokens_used=tokens_used,
            cost_cents=cost_cents,
        )
        self.db.add(usage_log)

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def check_feature_access(
        self,
        user_id: UUID,
        feature: str,
    ) -> bool:
        """Check if user has access to a feature.

        Args:
            user_id: User ID.
            feature: Feature name (e.g., "proposal_enhance", "auto_apply").

        Returns:
            True if user has access.

        Raises:
            FeatureNotAvailable: If feature is not available in user's tier.
        """
        subscription = await self.get_or_create_subscription(user_id)

        if not subscription.has_feature(feature):
            raise FeatureNotAvailable(
                feature=feature,
                current_tier=subscription.tier.value,
                required_tier=self._get_minimum_tier_for_feature(feature),
            )

        return True

    async def check_tone_access(
        self,
        user_id: UUID,
        tone: str,
    ) -> bool:
        """Check if user can use a specific proposal tone.

        Args:
            user_id: User ID.
            tone: Proposal tone (short/medium/full).

        Returns:
            True if user can use the tone.

        Raises:
            FeatureNotAvailable: If tone is not available in user's tier.
        """
        subscription = await self.get_or_create_subscription(user_id)

        if not subscription.can_use_tone(tone):
            raise FeatureNotAvailable(
                feature=f"proposal_tone_{tone}",
                current_tier=subscription.tier.value,
                required_tier="starter",
            )

        return True

    async def get_usage_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get current usage statistics for a user.

        Args:
            user_id: User ID.

        Returns:
            Usage statistics dictionary.
        """
        subscription = await self.get_or_create_subscription(user_id)
        subscription = await self._reset_counters_if_needed(subscription)

        limits = subscription.tier_limits

        return {
            "tier": subscription.tier.value,
            "proposals": {
                "used": subscription.proposal_count,
                "limit": limits.get("proposals_per_month", 5),
                "remaining": subscription.proposals_remaining,
                "reset_date": subscription.usage_reset_date.isoformat() if subscription.usage_reset_date else None,
            },
            "jd_parses": {
                "used": subscription.jd_parse_count,
                "limit": limits.get("jd_parses_per_month", 10),
                "remaining": subscription.jd_parses_remaining,
                "reset_date": subscription.usage_reset_date.isoformat() if subscription.usage_reset_date else None,
            },
            "job_searches": {
                "used": subscription.job_search_count_today,
                "limit": limits.get("job_searches_per_day", 3),
                "remaining": subscription.searches_remaining_today,
                "reset_date": subscription.daily_reset_date.isoformat() if subscription.daily_reset_date else None,
            },
            "features": limits.get("features", {}),
            "is_active": subscription.is_active,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        }

    async def upgrade_subscription(
        self,
        user_id: UUID,
        new_tier: SubscriptionTier,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        stripe_price_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Subscription:
        """Upgrade a user's subscription tier.

        Args:
            user_id: User ID.
            new_tier: New subscription tier.
            stripe_customer_id: Stripe customer ID.
            stripe_subscription_id: Stripe subscription ID.
            stripe_price_id: Stripe price ID.
            period_start: Billing period start.
            period_end: Billing period end.

        Returns:
            Updated subscription.
        """
        subscription = await self.get_or_create_subscription(user_id)

        subscription.tier = new_tier
        if stripe_customer_id:
            subscription.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            subscription.stripe_subscription_id = stripe_subscription_id
        if stripe_price_id:
            subscription.stripe_price_id = stripe_price_id
        if period_start:
            subscription.current_period_start = period_start
        if period_end:
            subscription.current_period_end = period_end

        # Reset usage counters on upgrade
        subscription.proposal_count = 0
        subscription.jd_parse_count = 0
        subscription.job_search_count_today = 0
        subscription.usage_reset_date = self._get_next_month_reset()
        subscription.daily_reset_date = date.today()

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(f"Upgraded user {user_id} to {new_tier.value} tier")

        return subscription

    async def cancel_subscription(
        self,
        user_id: UUID,
        at_period_end: bool = True,
    ) -> Subscription:
        """Cancel a subscription.

        Args:
            user_id: User ID.
            at_period_end: If True, cancel at end of billing period.

        Returns:
            Updated subscription.
        """
        subscription = await self.get_or_create_subscription(user_id)

        if at_period_end:
            subscription.cancel_at_period_end = True
        else:
            subscription.tier = SubscriptionTier.FREE
            subscription.canceled_at = datetime.utcnow()
            subscription.stripe_subscription_id = None

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(f"Canceled subscription for user {user_id}")

        return subscription

    async def handle_stripe_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> Optional[Subscription]:
        """Handle Stripe webhook events.

        Args:
            event_type: Stripe event type.
            event_data: Event payload.

        Returns:
            Updated subscription or None.
        """
        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            return await handler(event_data)

        logger.debug(f"Unhandled Stripe event: {event_type}")
        return None

    async def _handle_subscription_created(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle subscription.created event."""
        subscription_data = data.get("object", {})
        customer_id = subscription_data.get("customer")

        # Find user by stripe_customer_id
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            tier = self._get_tier_from_price(subscription_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id"))
            subscription.tier = tier
            subscription.stripe_subscription_id = subscription_data.get("id")
            subscription.current_period_start = datetime.fromtimestamp(subscription_data.get("current_period_start", 0))
            subscription.current_period_end = datetime.fromtimestamp(subscription_data.get("current_period_end", 0))
            await self.db.commit()

        return subscription

    async def _handle_subscription_updated(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle subscription.updated event."""
        subscription_data = data.get("object", {})
        stripe_sub_id = subscription_data.get("id")

        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.current_period_start = datetime.fromtimestamp(subscription_data.get("current_period_start", 0))
            subscription.current_period_end = datetime.fromtimestamp(subscription_data.get("current_period_end", 0))
            subscription.cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)

            if subscription_data.get("status") == "canceled":
                subscription.tier = SubscriptionTier.FREE
                subscription.canceled_at = datetime.utcnow()

            await self.db.commit()

        return subscription

    async def _handle_subscription_deleted(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle subscription.deleted event."""
        subscription_data = data.get("object", {})
        stripe_sub_id = subscription_data.get("id")

        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.tier = SubscriptionTier.FREE
            subscription.canceled_at = datetime.utcnow()
            subscription.stripe_subscription_id = None
            await self.db.commit()

        return subscription

    async def _handle_invoice_paid(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle invoice.paid event - reset usage counters."""
        invoice_data = data.get("object", {})
        customer_id = invoice_data.get("customer")

        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Reset monthly counters
            subscription.proposal_count = 0
            subscription.jd_parse_count = 0
            subscription.usage_reset_date = self._get_next_month_reset()
            await self.db.commit()

        return subscription

    async def _handle_payment_failed(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle invoice.payment_failed event."""
        invoice_data = data.get("object", {})
        customer_id = invoice_data.get("customer")

        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Mark payment as failed in metadata
            subscription.metadata = {
                **subscription.metadata,
                "payment_failed": True,
                "payment_failed_at": datetime.utcnow().isoformat(),
            }
            await self.db.commit()

        return subscription

    async def _check_limit(self, subscription: Subscription, action: UsageActionType) -> None:
        """Check if an action is within limits.

        Raises:
            UsageLimitExceeded: If limit exceeded.
        """
        limits = subscription.tier_limits

        if action == UsageActionType.PROPOSAL_GENERATE:
            limit = limits.get("proposals_per_month", 5)
            if limit != float("inf") and subscription.proposal_count >= limit:
                raise UsageLimitExceeded(
                    action="proposals",
                    limit=int(limit),
                    used=subscription.proposal_count,
                    reset_date=subscription.usage_reset_date,
                )

        elif action == UsageActionType.JD_PARSE:
            limit = limits.get("jd_parses_per_month", 10)
            if limit != float("inf") and subscription.jd_parse_count >= limit:
                raise UsageLimitExceeded(
                    action="JD parses",
                    limit=int(limit),
                    used=subscription.jd_parse_count,
                    reset_date=subscription.usage_reset_date,
                )

        elif action == UsageActionType.JOB_SEARCH:
            limit = limits.get("job_searches_per_day", 3)
            if limit != float("inf") and subscription.job_search_count_today >= limit:
                raise UsageLimitExceeded(
                    action="job searches",
                    limit=int(limit),
                    used=subscription.job_search_count_today,
                    reset_date=subscription.daily_reset_date + timedelta(days=1) if subscription.daily_reset_date else None,
                )

        elif action == UsageActionType.PROPOSAL_ENHANCE:
            if not subscription.has_feature("proposal_enhance"):
                raise FeatureNotAvailable(
                    feature="proposal_enhance",
                    current_tier=subscription.tier.value,
                    required_tier="starter",
                )

    async def _increment_counter(self, subscription: Subscription, action: UsageActionType) -> None:
        """Increment the appropriate usage counter."""
        if action == UsageActionType.PROPOSAL_GENERATE:
            subscription.proposal_count += 1
        elif action == UsageActionType.JD_PARSE:
            subscription.jd_parse_count += 1
        elif action == UsageActionType.JOB_SEARCH:
            subscription.job_search_count_today += 1
        # PROPOSAL_ENHANCE and RESUME_PARSE don't have counters (feature-gated)

    async def _reset_counters_if_needed(self, subscription: Subscription) -> Subscription:
        """Reset usage counters if reset dates have passed."""
        today = date.today()
        changed = False

        # Reset monthly counters
        if subscription.usage_reset_date and today >= subscription.usage_reset_date:
            subscription.proposal_count = 0
            subscription.jd_parse_count = 0
            subscription.usage_reset_date = self._get_next_month_reset()
            changed = True

        # Reset daily counters
        if subscription.daily_reset_date and today > subscription.daily_reset_date:
            subscription.job_search_count_today = 0
            subscription.daily_reset_date = today
            changed = True

        if changed:
            await self.db.commit()
            await self.db.refresh(subscription)

        return subscription

    def _get_next_month_reset(self) -> date:
        """Get the first day of next month."""
        today = date.today()
        if today.month == 12:
            return date(today.year + 1, 1, 1)
        return date(today.year, today.month + 1, 1)

    def _get_tier_from_price(self, price_id: Optional[str]) -> SubscriptionTier:
        """Map Stripe price ID to subscription tier."""
        # This would be configured with actual Stripe price IDs
        price_to_tier = {
            # Add your Stripe price IDs here
            # "price_starter_monthly": SubscriptionTier.STARTER,
            # "price_pro_monthly": SubscriptionTier.PRO,
            # "price_power_monthly": SubscriptionTier.POWER,
        }
        return price_to_tier.get(price_id, SubscriptionTier.FREE)

    def _get_minimum_tier_for_feature(self, feature: str) -> str:
        """Get the minimum tier that includes a feature."""
        for tier_name in ["starter", "pro", "power"]:
            tier_limits = TIER_LIMITS.get(tier_name, {})
            features = tier_limits.get("features", {})
            if features.get(feature):
                return tier_name
        return "power"


def get_subscription_service(db: AsyncSession) -> SubscriptionService:
    """Factory function to create SubscriptionService.

    Args:
        db: Database session.

    Returns:
        SubscriptionService instance.
    """
    return SubscriptionService(db)
