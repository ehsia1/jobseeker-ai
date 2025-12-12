"""
Integration tests for subscription routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, date

from backend.config import Settings


class TestGetSubscription:
    """Tests for GET /api/subscription/."""

    @pytest.mark.asyncio
    async def test_get_subscription_success(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test getting user subscription with usage info."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="free",
            proposal_count=5,
            jd_parse_count=3,
            job_search_count_today=10,
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user.id)
        assert "tier" in data
        assert "proposals_remaining" in data
        assert "tier_limits" in data

    @pytest.mark.asyncio
    async def test_get_subscription_creates_if_missing(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test subscription is created if user doesn't have one."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user.id)
        assert data["tier"] == "free"

    @pytest.mark.asyncio
    async def test_get_subscription_unauthorized(self, test_client: AsyncClient):
        """Test getting subscription without auth fails."""
        response = await test_client.get("/subscription/")

        assert response.status_code == 401


class TestGetUsageStats:
    """Tests for GET /api/subscription/usage."""

    @pytest.mark.asyncio
    async def test_get_usage_stats_success(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test getting usage statistics."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="starter",
            proposal_count=10,
            jd_parse_count=5,
            job_search_count_today=20,
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/usage", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "proposals_used" in data
        assert "proposals_limit" in data
        assert "proposals_remaining" in data
        assert "jd_parses_used" in data
        assert "job_searches_used_today" in data
        assert "features" in data

    @pytest.mark.asyncio
    async def test_get_usage_stats_unlimited_tier(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test usage stats for power tier with unlimited values."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="power")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/usage", headers=headers)

        assert response.status_code == 200
        data = response.json()
        # Power tier should have -1 (unlimited) for most limits
        assert data["tier"] == "power"

    @pytest.mark.asyncio
    async def test_get_usage_stats_unauthorized(self, test_client: AsyncClient):
        """Test getting usage stats without auth fails."""
        response = await test_client.get("/subscription/usage")

        assert response.status_code == 401


class TestGetPricing:
    """Tests for GET /api/subscription/pricing."""

    @pytest.mark.asyncio
    async def test_get_pricing_unauthenticated(self, test_client: AsyncClient):
        """Test getting pricing without authentication."""
        response = await test_client.get("/subscription/pricing")

        assert response.status_code == 200
        data = response.json()
        assert "tiers" in data
        assert isinstance(data["tiers"], list)
        assert len(data["tiers"]) >= 3  # At least free, starter, pro
        assert data["current_tier"] is None

    @pytest.mark.asyncio
    async def test_get_pricing_authenticated(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test getting pricing with authentication shows current tier."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="pro")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/pricing", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "tiers" in data
        assert data["current_tier"] == "pro"

    @pytest.mark.asyncio
    async def test_get_pricing_tier_info(self, test_client: AsyncClient):
        """Test pricing returns correct tier information."""
        response = await test_client.get("/subscription/pricing")

        assert response.status_code == 200
        data = response.json()

        # Check tier structure
        for tier in data["tiers"]:
            assert "id" in tier
            assert "name" in tier
            assert "price_cents" in tier
            assert "price_display" in tier
            assert "limits" in tier
            assert "popular" in tier

            # Check limits structure
            limits = tier["limits"]
            assert "proposals_per_month" in limits
            assert "jd_parses_per_month" in limits
            assert "job_searches_per_day" in limits
            assert "features" in limits


class TestCreateCheckout:
    """Tests for POST /api/subscription/checkout."""

    @pytest.mark.asyncio
    async def test_create_checkout_success(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test creating checkout session successfully."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="free")
        await db_session.commit()

        headers = auth_headers(user.username)

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session123"
        mock_session.id = "session_123"

        mock_customer = MagicMock()
        mock_customer.id = "cus_123"

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True), \
             patch("backend.api.routes.subscription.settings.stripe_secret_key", "sk_test"), \
             patch("backend.api.routes.subscription.settings.stripe_price_starter", "price_starter"), \
             patch("stripe.Customer.create", return_value=mock_customer), \
             patch("stripe.checkout.Session.create", return_value=mock_session):
            response = await test_client.post(
                "/subscription/checkout",
                json={
                    "tier": "starter",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
                headers=headers
            )

        assert response.status_code == 200
        if response.status_code == 200:
            data = response.json()
            assert "checkout_url" in data
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_create_checkout_free_tier_fails(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test checkout for free tier fails."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True):
            response = await test_client.post(
                "/subscription/checkout",
                json={
                    "tier": "free",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
                headers=headers
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_checkout_unauthorized(self, test_client: AsyncClient):
        """Test checkout without auth fails."""
        response = await test_client.post(
            "/subscription/checkout",
            json={
                "tier": "starter",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_checkout_stripe_not_configured(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test checkout fails when Stripe not configured."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=False):
            response = await test_client.post(
                "/subscription/checkout",
                json={
                    "tier": "starter",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
                headers=headers
            )

        assert response.status_code == 503


class TestCreatePortal:
    """Tests for POST /api/subscription/portal."""

    @pytest.mark.asyncio
    async def test_create_portal_success(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test creating portal session successfully."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="pro",
            stripe_customer_id="cus_existing",
        )
        await db_session.commit()

        headers = auth_headers(user.username)

        mock_portal = MagicMock()
        mock_portal.url = "https://billing.stripe.com/portal123"

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True), \
             patch("backend.api.routes.subscription.settings.stripe_secret_key", "sk_test"), \
             patch("stripe.billing_portal.Session.create", return_value=mock_portal):
            response = await test_client.post(
                "/subscription/portal",
                json={"return_url": "https://example.com/dashboard"},
                headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "portal_url" in data

    @pytest.mark.asyncio
    async def test_create_portal_no_stripe_customer(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test portal fails when user has no Stripe customer."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="free",
            stripe_customer_id=None,
        )
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True):
            response = await test_client.post(
                "/subscription/portal",
                json={"return_url": "https://example.com/dashboard"},
                headers=headers
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_portal_unauthorized(self, test_client: AsyncClient):
        """Test portal without auth fails."""
        response = await test_client.post(
            "/subscription/portal",
            json={"return_url": "https://example.com/dashboard"}
        )

        assert response.status_code == 401


class TestCancelSubscription:
    """Tests for POST /api/subscription/cancel."""

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test cancelling subscription at period end."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="pro",
            stripe_customer_id="cus_existing",
            stripe_subscription_id="sub_existing",
        )
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True), \
             patch("backend.api.routes.subscription.settings.stripe_secret_key", "sk_test"), \
             patch("stripe.Subscription.modify", return_value=MagicMock()):
            response = await test_client.post(
                "/subscription/cancel",
                json={"at_period_end": True},
                headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "end of the billing period" in data["message"]

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test cancelling subscription immediately."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="pro",
            stripe_customer_id="cus_existing",
            stripe_subscription_id="sub_existing",
        )
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True), \
             patch("backend.api.routes.subscription.settings.stripe_secret_key", "sk_test"), \
             patch("stripe.Subscription.delete", return_value=MagicMock()):
            response = await test_client.post(
                "/subscription/cancel",
                json={"at_period_end": False},
                headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "immediately" in data["message"]

    @pytest.mark.asyncio
    async def test_cancel_subscription_no_active_sub(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test cancel fails when no active subscription."""
        user = await user_factory()
        subscription = await subscription_factory(
            user=user,
            tier="free",
            stripe_subscription_id=None,
        )
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True):
            response = await test_client.post(
                "/subscription/cancel",
                json={"at_period_end": True},
                headers=headers
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_subscription_unauthorized(self, test_client: AsyncClient):
        """Test cancel without auth fails."""
        response = await test_client.post(
            "/subscription/cancel",
            json={"at_period_end": True}
        )

        assert response.status_code == 401


class TestStripeWebhook:
    """Tests for POST /api/subscription/webhook."""

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, test_client: AsyncClient):
        """Test webhook with invalid signature fails."""
        import stripe

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True), \
             patch("backend.api.routes.subscription.settings.stripe_webhook_secret", "whsec_test"), \
             patch("backend.api.routes.subscription.settings.stripe_secret_key", "sk_test"), \
             patch("stripe.Webhook.construct_event", side_effect=stripe.error.SignatureVerificationError("Invalid", "")):
            response = await test_client.post(
                "/subscription/webhook",
                content=b'{"test": "data"}',
                headers={"stripe-signature": "invalid_sig"}
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_not_configured(self, test_client: AsyncClient):
        """Test webhook fails when not configured."""
        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=False):
            response = await test_client.post(
                "/subscription/webhook",
                content=b'{"test": "data"}',
                headers={"stripe-signature": "sig"}
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_webhook_checkout_completed(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session
    ):
        """Test webhook handles checkout.session.completed event."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="free")
        await db_session.commit()

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "user_id": str(user.id),
                        "tier": "starter",
                    },
                    "subscription": "sub_new_123",
                }
            }
        }

        with patch.object(Settings, "stripe_configured", new_callable=PropertyMock, return_value=True), \
             patch("backend.api.routes.subscription.settings.stripe_webhook_secret", "whsec_test"), \
             patch("backend.api.routes.subscription.settings.stripe_secret_key", "sk_test"), \
             patch("stripe.Webhook.construct_event", return_value=event):
            response = await test_client.post(
                "/subscription/webhook",
                content=b'{"test": "data"}',
                headers={"stripe-signature": "valid_sig"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestSubscriptionTierLimits:
    """Tests for subscription tier limits enforcement."""

    @pytest.mark.asyncio
    async def test_free_tier_limits(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test free tier has correct limits."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="free")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/usage", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "free"
        # Free tier should have limited proposals
        assert data["proposals_limit"] >= 0

    @pytest.mark.asyncio
    async def test_starter_tier_limits(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test starter tier has higher limits than free."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="starter")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/usage", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "starter"
        # Starter tier should have more proposals than free
        assert data["proposals_limit"] > 5  # Assuming free has <=5

    @pytest.mark.asyncio
    async def test_pro_tier_features(
        self, test_client: AsyncClient, user_factory, subscription_factory, db_session, auth_headers
    ):
        """Test pro tier has expected features."""
        user = await user_factory()
        subscription = await subscription_factory(user=user, tier="pro")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/subscription/usage", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "pro"
        # Pro tier should have premium features
        features = data.get("features", {})
        assert "proposal_enhance" in features or "analytics" in features
