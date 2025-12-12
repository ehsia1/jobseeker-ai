"""
Integration tests for user management routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal


class TestGetProfile:
    """Tests for GET /users/profile."""

    @pytest.mark.asyncio
    async def test_get_profile_success(
        self, test_client: AsyncClient, user_factory, profile_factory, db_session, auth_headers
    ):
        """Test getting user profile successfully."""
        user = await user_factory()
        profile = await profile_factory(
            user=user,
            skills=["Python", "FastAPI", "PostgreSQL"],
            experience_years=5
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/users/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["skills"] == ["Python", "FastAPI", "PostgreSQL"]
        assert data["experience_years"] == 5

    @pytest.mark.asyncio
    async def test_get_profile_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting profile when it doesn't exist."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/users/profile", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_profile_unauthorized(self, test_client: AsyncClient):
        """Test getting profile without auth fails."""
        response = await test_client.get("/users/profile")

        assert response.status_code == 401


class TestUpdateProfile:
    """Tests for PUT /users/profile."""

    @pytest.mark.asyncio
    async def test_update_profile_create(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test creating profile via update when none exists."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            "/users/profile",
            json={
                "profession": "software_engineer",
                "job_title": "Senior Developer",
                "skills": ["Python", "FastAPI"],
                "experience_years": 8,
                "min_rate_usd": 120000,
                "preferences": {"remote_only": True}
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profession"] == "software_engineer"
        assert data["skills"] == ["Python", "FastAPI"]
        assert data["experience_years"] == 8

    @pytest.mark.asyncio
    async def test_update_profile_existing(
        self, test_client: AsyncClient, user_factory, profile_factory, db_session, auth_headers
    ):
        """Test updating existing profile."""
        user = await user_factory()
        profile = await profile_factory(
            user=user,
            skills=["Python"],
            experience_years=3
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            "/users/profile",
            json={
                "skills": ["Python", "FastAPI", "Docker"],
                "experience_years": 5,
                "job_title": "Senior Engineer"
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "Docker" in data["skills"]
        assert data["experience_years"] == 5

    @pytest.mark.asyncio
    async def test_update_profile_partial(
        self, test_client: AsyncClient, user_factory, profile_factory, db_session, auth_headers
    ):
        """Test partial profile update."""
        user = await user_factory()
        profile = await profile_factory(
            user=user,
            skills=["Python"],
            experience_years=3
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            "/users/profile",
            json={"experience_years": 7},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["experience_years"] == 7
        # Other fields should remain unchanged
        assert "Python" in data["skills"]


class TestDeleteProfile:
    """Tests for DELETE /users/profile."""

    @pytest.mark.asyncio
    async def test_delete_profile_success(
        self, test_client: AsyncClient, user_factory, profile_factory, db_session, auth_headers
    ):
        """Test deleting profile successfully."""
        user = await user_factory()
        profile = await profile_factory(user=user)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.delete("/users/profile", headers=headers)

        assert response.status_code == 200

        # Verify profile is deleted
        get_response = await test_client.get("/users/profile", headers=headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test deleting non-existent profile returns success (idempotent)."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.delete("/users/profile", headers=headers)

        # Route is idempotent - returns success even if no profile exists
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestGetCurrentUserDetailed:
    """Tests for GET /users/me."""

    @pytest.mark.asyncio
    async def test_get_me_detailed(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting detailed current user info."""
        user = await user_factory(
            email="detailed@example.com",
            username="detaileduser",
            is_premium=True
        )
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/users/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "detailed@example.com"
        assert data["username"] == "detaileduser"
        assert data["is_premium"] is True


class TestNotifications:
    """Tests for notification endpoints."""

    @pytest.mark.asyncio
    async def test_get_notifications(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting user notifications."""
        from backend.models.notification import Notification

        user = await user_factory()

        # Create notifications with correct model fields
        notification1 = Notification(
            id=uuid4(),
            user_id=user.id,
            type="email",
            subject="New Job Match",
            content="Found a job matching your profile",
            read=False,
        )
        notification2 = Notification(
            id=uuid4(),
            user_id=user.id,
            type="email",
            subject="Welcome",
            content="Welcome to JobSeeker AI!",
            read=True,
        )
        db_session.add(notification1)
        db_session.add(notification2)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/users/me/notifications", headers=headers)

        assert response.status_code == 200
        data = response.json()
        # API returns paginated response
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_get_notifications_pagination(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test notification pagination."""
        from backend.models.notification import Notification

        user = await user_factory()

        # Create several notifications
        for i in range(5):
            notification = Notification(
                id=uuid4(),
                user_id=user.id,
                type="email",
                subject=f"Notification {i}",
                content=f"Content {i}",
                read=False,
            )
            db_session.add(notification)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get(
            "/users/me/notifications",
            params={"page": 1, "size": 2},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2

    @pytest.mark.asyncio
    async def test_mark_notification_read(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test marking notification as read."""
        from backend.models.notification import Notification

        user = await user_factory()

        notification = Notification(
            id=uuid4(),
            user_id=user.id,
            type="email",
            subject="New Match",
            content="Found a job",
            read=False,
        )
        db_session.add(notification)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            f"/users/me/notifications/{notification.id}/read",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["read"] is True

    @pytest.mark.asyncio
    async def test_mark_notification_read_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test marking non-existent notification as read."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_id = str(uuid4())
        response = await test_client.put(
            f"/users/me/notifications/{fake_id}/read",
            headers=headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_all_notifications_read(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test marking all notifications as read."""
        from backend.models.notification import Notification

        user = await user_factory()

        for i in range(3):
            notification = Notification(
                id=uuid4(),
                user_id=user.id,
                type="email",
                subject=f"Match {i}",
                content=f"Job {i}",
                read=False,
            )
            db_session.add(notification)
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.put(
            "/users/me/notifications/read-all",
            headers=headers
        )

        assert response.status_code == 200

        # Verify all are read by checking notification objects
        get_response = await test_client.get(
            "/users/me/notifications",
            headers=headers
        )
        data = get_response.json()
        for notification in data["items"]:
            assert notification["read"] is True
