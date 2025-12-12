"""
Unit tests for the SubscriptionService.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from backend.services.subscription_service import (
    SubscriptionService,
    UsageLimitExceeded,
    FeatureNotAvailable,
    get_subscription_service,
)
from backend.models.subscription import (
    Subscription,
    SubscriptionTier,
    UsageActionType,
    TIER_LIMITS,
)


class TestUsageLimitExceeded:
    """Tests for UsageLimitExceeded exception."""

    def test_init(self):
        """Test exception initialization."""
        exc = UsageLimitExceeded(
            action="proposals",
            limit=5,
            used=5,
            reset_date=date(2024, 2, 1),
        )

        assert exc.action == "proposals"
        assert exc.limit == 5
        assert exc.used == 5
        assert exc.reset_date == date(2024, 2, 1)

    def test_message_with_reset_date(self):
        """Test exception message includes reset date."""
        exc = UsageLimitExceeded(
            action="proposals",
            limit=5,
            used=5,
            reset_date=date(2024, 2, 1),
        )

        assert "proposals" in str(exc)
        assert "5/5" in str(exc)
        assert "2024-02-01" in str(exc)

    def test_message_without_reset_date(self):
        """Test exception message without reset date."""
        exc = UsageLimitExceeded(
            action="proposals",
            limit=5,
            used=5,
        )

        assert "proposals" in str(exc)
        assert "5/5" in str(exc)


class TestFeatureNotAvailable:
    """Tests for FeatureNotAvailable exception."""

    def test_init(self):
        """Test exception initialization."""
        exc = FeatureNotAvailable(
            feature="proposal_enhance",
            current_tier="free",
            required_tier="starter",
        )

        assert exc.feature == "proposal_enhance"
        assert exc.current_tier == "free"
        assert exc.required_tier == "starter"

    def test_message(self):
        """Test exception message."""
        exc = FeatureNotAvailable(
            feature="auto_apply",
            current_tier="free",
            required_tier="pro",
        )

        assert "auto_apply" in str(exc)
        assert "free" in str(exc)
        assert "pro" in str(exc)


class TestSubscriptionServiceInit:
    """Tests for SubscriptionService initialization."""

    def test_init(self):
        """Test service initialization."""
        mock_db = MagicMock()

        service = SubscriptionService(db=mock_db)

        assert service.db == mock_db


class TestGetOrCreateSubscription:
    """Tests for get_or_create_subscription method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_existing_subscription(self, service, mock_db):
        """Test getting existing subscription."""
        user_id = uuid4()
        existing_sub = MagicMock(spec=Subscription)
        existing_sub.tier = SubscriptionTier.STARTER

        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_sub

        result = await service.get_or_create_subscription(user_id)

        assert result == existing_sub
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_free_subscription(self, service, mock_db):
        """Test creating free subscription when none exists."""
        user_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.get_or_create_subscription(user_id)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        # Check the subscription was created with FREE tier
        added_sub = mock_db.add.call_args[0][0]
        assert added_sub.tier == SubscriptionTier.FREE
        assert added_sub.user_id == user_id


class TestGetSubscription:
    """Tests for get_subscription method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_subscription_exists(self, service, mock_db):
        """Test getting existing subscription."""
        user_id = uuid4()
        existing_sub = MagicMock(spec=Subscription)

        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_sub

        result = await service.get_subscription(user_id)

        assert result == existing_sub

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, service, mock_db):
        """Test getting non-existent subscription."""
        user_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.get_subscription(user_id)

        assert result is None


class TestCheckAndRecordUsage:
    """Tests for check_and_record_usage method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.fixture
    def mock_subscription(self):
        """Create mock subscription."""
        sub = MagicMock(spec=Subscription)
        sub.id = uuid4()
        sub.tier = SubscriptionTier.STARTER
        sub.proposal_count = 2
        sub.jd_parse_count = 5
        sub.job_search_count_today = 1
        sub.usage_reset_date = date.today() + timedelta(days=30)
        sub.daily_reset_date = date.today()
        sub.tier_limits = TIER_LIMITS["starter"]
        sub.has_feature = MagicMock(return_value=True)
        return sub

    @pytest.mark.asyncio
    async def test_record_proposal_usage(self, service, mock_db, mock_subscription):
        """Test recording proposal generation usage."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        result = await service.check_and_record_usage(
            user_id=uuid4(),
            action=UsageActionType.PROPOSAL_GENERATE,
        )

        assert result == mock_subscription
        mock_db.add.assert_called()  # UsageLog added
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_record_jd_parse_usage(self, service, mock_db, mock_subscription):
        """Test recording JD parse usage."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        result = await service.check_and_record_usage(
            user_id=uuid4(),
            action=UsageActionType.JD_PARSE,
        )

        assert result == mock_subscription

    @pytest.mark.asyncio
    async def test_record_job_search_usage(self, service, mock_db, mock_subscription):
        """Test recording job search usage."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        result = await service.check_and_record_usage(
            user_id=uuid4(),
            action=UsageActionType.JOB_SEARCH,
        )

        assert result == mock_subscription

    @pytest.mark.asyncio
    async def test_record_usage_with_metadata(self, service, mock_db, mock_subscription):
        """Test recording usage with metadata."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        metadata = {"job_id": "123", "source": "upwork"}
        result = await service.check_and_record_usage(
            user_id=uuid4(),
            action=UsageActionType.PROPOSAL_GENERATE,
            metadata=metadata,
            tokens_used=500,
            cost_cents=2,
        )

        # Check UsageLog was created with metadata
        usage_log = mock_db.add.call_args[0][0]
        assert usage_log.metadata == metadata
        assert usage_log.tokens_used == 500
        assert usage_log.cost_cents == 2

    @pytest.mark.asyncio
    async def test_usage_limit_exceeded_proposals(self, service, mock_db, mock_subscription):
        """Test UsageLimitExceeded raised for proposals."""
        mock_subscription.proposal_count = 100  # Over limit
        mock_subscription.tier_limits = {"proposals_per_month": 50}
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        with pytest.raises(UsageLimitExceeded) as exc_info:
            await service.check_and_record_usage(
                user_id=uuid4(),
                action=UsageActionType.PROPOSAL_GENERATE,
            )

        assert exc_info.value.action == "proposals"

    @pytest.mark.asyncio
    async def test_usage_limit_exceeded_jd_parses(self, service, mock_db, mock_subscription):
        """Test UsageLimitExceeded raised for JD parses."""
        mock_subscription.jd_parse_count = 50
        mock_subscription.tier_limits = {"jd_parses_per_month": 25}
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        with pytest.raises(UsageLimitExceeded) as exc_info:
            await service.check_and_record_usage(
                user_id=uuid4(),
                action=UsageActionType.JD_PARSE,
            )

        assert exc_info.value.action == "JD parses"

    @pytest.mark.asyncio
    async def test_usage_limit_exceeded_job_searches(self, service, mock_db, mock_subscription):
        """Test UsageLimitExceeded raised for job searches."""
        mock_subscription.job_search_count_today = 10
        mock_subscription.tier_limits = {"job_searches_per_day": 5}
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        with pytest.raises(UsageLimitExceeded) as exc_info:
            await service.check_and_record_usage(
                user_id=uuid4(),
                action=UsageActionType.JOB_SEARCH,
            )

        assert exc_info.value.action == "job searches"


class TestCheckFeatureAccess:
    """Tests for check_feature_access method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_feature_available(self, service, mock_db):
        """Test feature is available."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.has_feature = MagicMock(return_value=True)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        result = await service.check_feature_access(uuid4(), "proposal_enhance")

        assert result is True

    @pytest.mark.asyncio
    async def test_feature_not_available(self, service, mock_db):
        """Test feature not available raises exception."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.tier = SubscriptionTier.FREE
        mock_sub.has_feature = MagicMock(return_value=False)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        with pytest.raises(FeatureNotAvailable) as exc_info:
            await service.check_feature_access(uuid4(), "proposal_enhance")

        assert exc_info.value.feature == "proposal_enhance"


class TestCheckToneAccess:
    """Tests for check_tone_access method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_tone_available(self, service, mock_db):
        """Test tone is available."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.can_use_tone = MagicMock(return_value=True)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        result = await service.check_tone_access(uuid4(), "full")

        assert result is True

    @pytest.mark.asyncio
    async def test_tone_not_available(self, service, mock_db):
        """Test tone not available raises exception."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.tier = SubscriptionTier.FREE
        mock_sub.can_use_tone = MagicMock(return_value=False)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        with pytest.raises(FeatureNotAvailable) as exc_info:
            await service.check_tone_access(uuid4(), "full")

        assert "proposal_tone_full" in exc_info.value.feature


class TestGetUsageStats:
    """Tests for get_usage_stats method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, service, mock_db):
        """Test getting usage statistics."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.tier = SubscriptionTier.STARTER
        mock_sub.proposal_count = 10
        mock_sub.jd_parse_count = 15
        mock_sub.job_search_count_today = 3
        mock_sub.usage_reset_date = date(2024, 2, 1)
        mock_sub.daily_reset_date = date(2024, 1, 15)
        mock_sub.current_period_end = datetime(2024, 2, 1, 0, 0, 0)
        mock_sub.is_active = True
        mock_sub.tier_limits = {
            "proposals_per_month": 50,
            "jd_parses_per_month": 25,
            "job_searches_per_day": 10,
            "features": {"proposal_enhance": True},
        }
        mock_sub.proposals_remaining = 40
        mock_sub.jd_parses_remaining = 10
        mock_sub.searches_remaining_today = 7

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        result = await service.get_usage_stats(uuid4())

        assert result["tier"] == "starter"
        assert result["proposals"]["used"] == 10
        assert result["proposals"]["limit"] == 50
        assert result["jd_parses"]["used"] == 15
        assert result["job_searches"]["used"] == 3
        assert result["is_active"] is True


class TestUpgradeSubscription:
    """Tests for upgrade_subscription method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.fixture
    def mock_subscription(self):
        """Create mock subscription."""
        sub = MagicMock(spec=Subscription)
        sub.tier = SubscriptionTier.FREE
        sub.proposal_count = 5
        sub.jd_parse_count = 10
        sub.job_search_count_today = 3
        return sub

    @pytest.mark.asyncio
    async def test_upgrade_subscription(self, service, mock_db, mock_subscription):
        """Test upgrading subscription tier."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        result = await service.upgrade_subscription(
            user_id=uuid4(),
            new_tier=SubscriptionTier.PRO,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_456",
        )

        assert result.tier == SubscriptionTier.PRO
        assert result.stripe_customer_id == "cus_123"
        assert result.stripe_subscription_id == "sub_456"
        # Counters should be reset
        assert result.proposal_count == 0
        assert result.jd_parse_count == 0
        assert result.job_search_count_today == 0

    @pytest.mark.asyncio
    async def test_upgrade_with_period_dates(self, service, mock_db, mock_subscription):
        """Test upgrading with billing period dates."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 2, 1)

        result = await service.upgrade_subscription(
            user_id=uuid4(),
            new_tier=SubscriptionTier.STARTER,
            period_start=period_start,
            period_end=period_end,
        )

        assert result.current_period_start == period_start
        assert result.current_period_end == period_end


class TestCancelSubscription:
    """Tests for cancel_subscription method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.add = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.fixture
    def mock_subscription(self):
        """Create mock subscription."""
        sub = MagicMock(spec=Subscription)
        sub.tier = SubscriptionTier.PRO
        sub.stripe_subscription_id = "sub_123"
        return sub

    @pytest.mark.asyncio
    async def test_cancel_at_period_end(self, service, mock_db, mock_subscription):
        """Test canceling at period end."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        result = await service.cancel_subscription(uuid4(), at_period_end=True)

        assert result.cancel_at_period_end is True
        # Should not change tier immediately
        assert result.tier == SubscriptionTier.PRO

    @pytest.mark.asyncio
    async def test_cancel_immediately(self, service, mock_db, mock_subscription):
        """Test canceling immediately."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_subscription

        result = await service.cancel_subscription(uuid4(), at_period_end=False)

        assert result.tier == SubscriptionTier.FREE
        assert result.stripe_subscription_id is None


class TestStripeWebhooks:
    """Tests for Stripe webhook handlers."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.commit = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_handle_subscription_created(self, service, mock_db):
        """Test handling subscription.created event."""
        mock_sub = MagicMock(spec=Subscription)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        event_data = {
            "object": {
                "id": "sub_123",
                "customer": "cus_456",
                "current_period_start": 1704067200,
                "current_period_end": 1706745600,
                "items": {"data": [{"price": {"id": "price_starter"}}]},
            }
        }

        result = await service.handle_stripe_webhook(
            "customer.subscription.created", event_data
        )

        assert result == mock_sub
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_handle_subscription_updated(self, service, mock_db):
        """Test handling subscription.updated event."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.tier = SubscriptionTier.STARTER
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        event_data = {
            "object": {
                "id": "sub_123",
                "status": "active",
                "current_period_start": 1704067200,
                "current_period_end": 1706745600,
                "cancel_at_period_end": False,
            }
        }

        result = await service.handle_stripe_webhook(
            "customer.subscription.updated", event_data
        )

        assert result == mock_sub

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted(self, service, mock_db):
        """Test handling subscription.deleted event."""
        mock_sub = MagicMock(spec=Subscription)
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        event_data = {"object": {"id": "sub_123"}}

        result = await service.handle_stripe_webhook(
            "customer.subscription.deleted", event_data
        )

        assert result.tier == SubscriptionTier.FREE
        assert result.stripe_subscription_id is None

    @pytest.mark.asyncio
    async def test_handle_invoice_paid(self, service, mock_db):
        """Test handling invoice.paid event."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.proposal_count = 50
        mock_sub.jd_parse_count = 25
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        event_data = {"object": {"customer": "cus_123"}}

        result = await service.handle_stripe_webhook("invoice.paid", event_data)

        # Counters should be reset
        assert result.proposal_count == 0
        assert result.jd_parse_count == 0

    @pytest.mark.asyncio
    async def test_handle_payment_failed(self, service, mock_db):
        """Test handling invoice.payment_failed event."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.metadata = {}
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_sub

        event_data = {"object": {"customer": "cus_123"}}

        result = await service.handle_stripe_webhook(
            "invoice.payment_failed", event_data
        )

        # Should mark payment as failed in metadata
        assert result.metadata["payment_failed"] is True

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self, service, mock_db):
        """Test handling unknown event type."""
        result = await service.handle_stripe_webhook(
            "unknown.event", {"object": {}}
        )

        assert result is None


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def service(self):
        """Create service."""
        mock_db = MagicMock()
        return SubscriptionService(db=mock_db)

    def test_get_next_month_reset(self, service):
        """Test getting next month reset date."""
        result = service._get_next_month_reset()

        today = date.today()
        if today.month == 12:
            expected = date(today.year + 1, 1, 1)
        else:
            expected = date(today.year, today.month + 1, 1)

        assert result == expected

    def test_get_tier_from_price(self, service):
        """Test mapping price ID to tier."""
        # Unknown price ID returns FREE
        result = service._get_tier_from_price("unknown_price")

        assert result == SubscriptionTier.FREE

    def test_get_minimum_tier_for_feature(self, service):
        """Test getting minimum tier for feature."""
        # Features that require specific tiers
        result = service._get_minimum_tier_for_feature("unknown_feature")

        # Should return highest tier for unknown features
        assert result == "power"


class TestGetSubscriptionService:
    """Tests for get_subscription_service factory function."""

    def test_get_subscription_service(self):
        """Test factory function creates service."""
        mock_db = MagicMock()

        service = get_subscription_service(mock_db)

        assert isinstance(service, SubscriptionService)
        assert service.db == mock_db


class TestResetCountersIfNeeded:
    """Tests for _reset_counters_if_needed method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create service."""
        return SubscriptionService(db=mock_db)

    @pytest.mark.asyncio
    async def test_reset_monthly_counters(self, service, mock_db):
        """Test monthly counters reset when date has passed."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.proposal_count = 10
        mock_sub.jd_parse_count = 20
        mock_sub.job_search_count_today = 5
        mock_sub.usage_reset_date = date.today() - timedelta(days=1)
        mock_sub.daily_reset_date = date.today()

        result = await service._reset_counters_if_needed(mock_sub)

        assert result.proposal_count == 0
        assert result.jd_parse_count == 0
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_reset_daily_counters(self, service, mock_db):
        """Test daily counters reset when date has passed."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.proposal_count = 10
        mock_sub.jd_parse_count = 20
        mock_sub.job_search_count_today = 5
        mock_sub.usage_reset_date = date.today() + timedelta(days=30)
        mock_sub.daily_reset_date = date.today() - timedelta(days=1)

        result = await service._reset_counters_if_needed(mock_sub)

        assert result.job_search_count_today == 0
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_no_reset_needed(self, service, mock_db):
        """Test no reset when dates haven't passed."""
        mock_sub = MagicMock(spec=Subscription)
        mock_sub.proposal_count = 10
        mock_sub.jd_parse_count = 20
        mock_sub.job_search_count_today = 5
        mock_sub.usage_reset_date = date.today() + timedelta(days=30)
        mock_sub.daily_reset_date = date.today()

        result = await service._reset_counters_if_needed(mock_sub)

        # Counters should not be changed
        assert result.proposal_count == 10
        assert result.jd_parse_count == 20
        assert result.job_search_count_today == 5
        mock_db.commit.assert_not_called()
