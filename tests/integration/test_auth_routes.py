"""
Integration tests for authentication routes.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from backend.api.main import app
from backend.database import get_db


class TestRegister:
    """Tests for POST /auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, test_client: AsyncClient):
        """Test successful user registration."""
        response = await test_client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_client: AsyncClient, user_factory, db_session):
        """Test registration with existing email fails."""
        # Create existing user
        existing_user = await user_factory(email="existing@example.com")
        await db_session.commit()

        response = await test_client.post(
            "/auth/register",
            json={
                "email": "existing@example.com",
                "username": "different_user",
                "password": "SecurePass123!",
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, test_client: AsyncClient, user_factory, db_session):
        """Test registration with existing username fails."""
        existing_user = await user_factory(username="existinguser")
        await db_session.commit()

        response = await test_client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "username": "existinguser",
                "password": "SecurePass123!",
            }
        )

        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, test_client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await test_client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "username": "validuser",
                "password": "SecurePass123!",
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, test_client: AsyncClient):
        """Test registration with weak password fails."""
        response = await test_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "username": "validuser",
                "password": "123",  # Too short
            }
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient, user_factory, db_session):
        """Test successful login."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "TestPassword123!"

        user = await user_factory(email="login@example.com", username="loginuser")
        user.password_hash = pwd_context.hash(password)
        await db_session.commit()

        response = await test_client.post(
            "/auth/login",
            data={
                "username": "login@example.com",
                "password": password,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, test_client: AsyncClient):
        """Test login with non-existent email fails."""
        response = await test_client.post(
            "/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!",
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client: AsyncClient, user_factory, db_session):
        """Test login with wrong password fails."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user = await user_factory(email="wrongpwd@example.com")
        user.password_hash = pwd_context.hash("CorrectPassword123!")
        await db_session.commit()

        response = await test_client.post(
            "/auth/login",
            data={
                "username": "wrongpwd@example.com",
                "password": "WrongPassword123!",
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, test_client: AsyncClient, user_factory, db_session):
        """Test login with inactive user fails."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "TestPassword123!"

        user = await user_factory(email="inactive@example.com", is_active=False)
        user.password_hash = pwd_context.hash(password)
        await db_session.commit()

        response = await test_client.post(
            "/auth/login",
            data={
                "username": "inactive@example.com",
                "password": password,
            }
        )

        assert response.status_code == 401


class TestGetCurrentUser:
    """Tests for GET /auth/me."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting current user with valid token."""
        user = await user_factory(email="me@example.com", username="meuser")
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["username"] == "meuser"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, test_client: AsyncClient):
        """Test getting current user without token fails."""
        response = await test_client.get("/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await test_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, test_client: AsyncClient, user_factory, db_session):
        """Test getting current user with expired token fails."""
        from datetime import datetime, timedelta
        from jose import jwt

        user = await user_factory()
        await db_session.commit()

        # Create expired token
        payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")

        response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


class TestRefreshToken:
    """Tests for POST /auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test successful token refresh."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post("/auth/refresh", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_no_auth(self, test_client: AsyncClient):
        """Test refresh without token fails."""
        response = await test_client.post("/auth/refresh")

        assert response.status_code == 401
