"""
Integration tests for interview coaching routes.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock


class TestCreateSession:
    """Tests for POST /interview/sessions."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test creating an interview session successfully."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "target_role": "Software Engineer",
                    "target_company": "TechCorp",
                    "total_questions": 5
                },
                headers=headers
            )

        assert response.status_code == 201
        data = response.json()
        assert "session" in data
        assert data["session"]["interview_type"] == "behavioral"
        assert data["session"]["difficulty"] == "mid"
        assert data["session"]["target_role"] == "Software Engineer"
        assert data["session"]["total_questions"] == 5
        assert "current_question" in data

    @pytest.mark.asyncio
    async def test_create_session_with_job(
        self, test_client: AsyncClient, user_factory, job_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test creating an interview session linked to a job."""
        user = await user_factory()
        job = await job_factory(title="Senior Python Developer")
        await db_session.commit()

        headers = auth_headers(user.username)

        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "technical",
                    "difficulty": "senior",
                    "job_id": str(job.id),
                    "total_questions": 3
                },
                headers=headers
            )

        assert response.status_code == 201
        data = response.json()
        assert data["session"]["job_id"] == str(job.id)

    @pytest.mark.asyncio
    async def test_create_session_all_interview_types(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test creating sessions with different interview types."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        interview_types = ["behavioral", "technical", "system_design", "case_study", "situational", "competency"]

        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            for interview_type in interview_types:
                response = await test_client.post(
                    "/interview/sessions",
                    json={
                        "interview_type": interview_type,
                        "difficulty": "mid",
                        "total_questions": 3
                    },
                    headers=headers
                )

                assert response.status_code == 201, f"Failed for type: {interview_type}"
                data = response.json()
                assert data["session"]["interview_type"] == interview_type

    @pytest.mark.asyncio
    async def test_create_session_all_difficulty_levels(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test creating sessions with different difficulty levels."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        difficulty_levels = ["entry", "mid", "senior", "lead", "executive"]

        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            for difficulty in difficulty_levels:
                response = await test_client.post(
                    "/interview/sessions",
                    json={
                        "interview_type": "behavioral",
                        "difficulty": difficulty,
                        "total_questions": 3
                    },
                    headers=headers
                )

                assert response.status_code == 201, f"Failed for difficulty: {difficulty}"
                data = response.json()
                assert data["session"]["difficulty"] == difficulty

    @pytest.mark.asyncio
    async def test_create_session_with_focus_areas(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test creating session with specific focus areas."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        focus_areas = ["leadership", "conflict resolution", "project management"]

        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "senior",
                    "focus_areas": focus_areas,
                    "total_questions": 5
                },
                headers=headers
            )

        assert response.status_code == 201
        data = response.json()
        assert data["session"]["focus_areas"] == focus_areas

    @pytest.mark.asyncio
    async def test_create_session_unauthorized(
        self, test_client: AsyncClient, db_session
    ):
        """Test creating session without auth fails (or uses demo mode)."""
        response = await test_client.post(
            "/interview/sessions",
            json={
                "interview_type": "behavioral",
                "difficulty": "mid",
                "total_questions": 5
            }
        )

        # Either unauthorized or demo mode allowed
        assert response.status_code in [201, 401]

    @pytest.mark.asyncio
    async def test_create_session_invalid_type(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test creating session with invalid interview type fails."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.post(
            "/interview/sessions",
            json={
                "interview_type": "invalid_type",
                "difficulty": "mid",
                "total_questions": 5
            },
            headers=headers
        )

        assert response.status_code == 422


class TestListSessions:
    """Tests for GET /interview/sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test listing sessions when user has none."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        response = await test_client.get("/interview/sessions", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test listing sessions after creating some."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create a few sessions
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            for _ in range(3):
                await test_client.post(
                    "/interview/sessions",
                    json={
                        "interview_type": "behavioral",
                        "difficulty": "mid",
                        "total_questions": 3
                    },
                    headers=headers
                )

        response = await test_client.get("/interview/sessions", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_sessions_with_limit(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test listing sessions with limit parameter."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create sessions
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            for _ in range(5):
                await test_client.post(
                    "/interview/sessions",
                    json={
                        "interview_type": "behavioral",
                        "difficulty": "mid",
                        "total_questions": 3
                    },
                    headers=headers
                )

        response = await test_client.get("/interview/sessions?limit=2", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2


class TestGetSession:
    """Tests for GET /interview/sessions/{session_id}."""

    @pytest.mark.asyncio
    async def test_get_session_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test getting a session by ID."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 5
                },
                headers=headers
            )

        session_id = create_response.json()["session"]["id"]

        # Get session
        response = await test_client.get(f"/interview/sessions/{session_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["interview_type"] == "behavioral"
        assert "questions" in data

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test getting a non-existent session."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_id = str(uuid4())
        response = await test_client.get(f"/interview/sessions/{fake_id}", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session_unauthorized(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test user cannot access another user's session."""
        user1 = await user_factory(username="user1", email="user1@test.com")
        user2 = await user_factory(username="user2", email="user2@test.com")
        await db_session.commit()

        headers1 = auth_headers(user1.username)
        headers2 = auth_headers(user2.username)

        # Create session for user1
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 3
                },
                headers=headers1
            )

        session_id = create_response.json()["session"]["id"]

        # Try to access with user2
        response = await test_client.get(f"/interview/sessions/{session_id}", headers=headers2)

        assert response.status_code == 403


class TestGetCurrentQuestion:
    """Tests for GET /interview/sessions/{session_id}/current-question."""

    @pytest.mark.asyncio
    async def test_get_current_question_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test getting current question."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 5
                },
                headers=headers
            )

        session_id = create_response.json()["session"]["id"]

        # Get current question
        response = await test_client.get(
            f"/interview/sessions/{session_id}/current-question",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "question" in data
        assert "session_progress" in data
        assert "is_session_complete" in data
        assert data["is_session_complete"] is False


class TestSubmitResponse:
    """Tests for POST /interview/sessions/{session_id}/questions/{question_id}/respond."""

    @pytest.mark.asyncio
    async def test_submit_response_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test submitting a response to a question."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 3
                },
                headers=headers
            )

        session_data = create_response.json()
        session_id = session_data["session"]["id"]
        question_id = session_data["current_question"]["id"]

        # Submit response
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                f"/interview/sessions/{session_id}/questions/{question_id}/respond",
                json={
                    "response": "I demonstrated leadership by organizing a cross-functional team to deliver a critical project on time. I set clear goals, delegated tasks, and maintained open communication throughout.",
                    "response_duration_seconds": 120
                },
                headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        assert "session_progress" in data
        assert "is_session_complete" in data

        feedback = data["feedback"]
        assert "score" in feedback
        assert "feedback" in feedback
        assert "strengths" in feedback
        assert "improvements" in feedback

    @pytest.mark.asyncio
    async def test_submit_response_progresses_session(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test that submitting responses progresses the session."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session with 2 questions
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 2
                },
                headers=headers
            )

        session_data = create_response.json()
        session_id = session_data["session"]["id"]
        question_id = session_data["current_question"]["id"]

        # Submit first response
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                f"/interview/sessions/{session_id}/questions/{question_id}/respond",
                json={
                    "response": "My response to the first question using the STAR method.",
                    "response_duration_seconds": 60
                },
                headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["session_progress"] == 50  # 1 of 2 completed
        assert data["is_session_complete"] is False
        assert data["next_question"] is not None

    @pytest.mark.asyncio
    async def test_submit_response_question_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test submitting response to non-existent question."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 3
                },
                headers=headers
            )

        session_id = create_response.json()["session"]["id"]
        fake_question_id = str(uuid4())

        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                f"/interview/sessions/{session_id}/questions/{fake_question_id}/respond",
                json={
                    "response": "Test response",
                    "response_duration_seconds": 60
                },
                headers=headers
            )

        assert response.status_code in [400, 404, 500]


class TestCompleteSession:
    """Tests for POST /interview/sessions/{session_id}/complete."""

    @pytest.mark.asyncio
    async def test_complete_session_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test completing an interview session."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session with 2 questions
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 2
                },
                headers=headers
            )

        session_data = create_response.json()
        session_id = session_data["session"]["id"]

        # Answer all questions
        current_question = session_data["current_question"]
        for i in range(2):
            with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
                submit_response = await test_client.post(
                    f"/interview/sessions/{session_id}/questions/{current_question['id']}/respond",
                    json={
                        "response": f"My response to question {i+1}",
                        "response_duration_seconds": 60
                    },
                    headers=headers
                )
                response_data = submit_response.json()
                if response_data.get("next_question"):
                    current_question = response_data["next_question"]

        # Complete session
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            response = await test_client.post(
                f"/interview/sessions/{session_id}/complete",
                headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "total_questions" in data
        assert "completed_questions" in data
        assert "feedback_summary" in data
        assert "strengths" in data
        assert "areas_to_improve" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_complete_session_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test completing non-existent session."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_id = str(uuid4())

        response = await test_client.post(
            f"/interview/sessions/{fake_id}/complete",
            headers=headers
        )

        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /interview/sessions/{session_id}."""

    @pytest.mark.asyncio
    async def test_delete_session_success(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test deleting a session."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)

        # Create session
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 3
                },
                headers=headers
            )

        session_id = create_response.json()["session"]["id"]

        # Delete session
        response = await test_client.delete(f"/interview/sessions/{session_id}", headers=headers)

        assert response.status_code == 204

        # Verify deleted
        get_response = await test_client.get(f"/interview/sessions/{session_id}", headers=headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session_not_found(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers
    ):
        """Test deleting non-existent session."""
        user = await user_factory()
        await db_session.commit()

        headers = auth_headers(user.username)
        fake_id = str(uuid4())

        response = await test_client.delete(f"/interview/sessions/{fake_id}", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session_unauthorized(
        self, test_client: AsyncClient, user_factory, db_session, auth_headers, mock_llm_service
    ):
        """Test user cannot delete another user's session."""
        user1 = await user_factory(username="user1", email="user1@test.com")
        user2 = await user_factory(username="user2", email="user2@test.com")
        await db_session.commit()

        headers1 = auth_headers(user1.username)
        headers2 = auth_headers(user2.username)

        # Create session for user1
        with patch("backend.services.interview_service.get_llm_service", return_value=mock_llm_service):
            create_response = await test_client.post(
                "/interview/sessions",
                json={
                    "interview_type": "behavioral",
                    "difficulty": "mid",
                    "total_questions": 3
                },
                headers=headers1
            )

        session_id = create_response.json()["session"]["id"]

        # Try to delete with user2
        response = await test_client.delete(f"/interview/sessions/{session_id}", headers=headers2)

        assert response.status_code == 403


class TestInterviewHealth:
    """Tests for GET /interview/health."""

    @pytest.mark.asyncio
    async def test_interview_health(self, test_client: AsyncClient):
        """Test interview service health check."""
        response = await test_client.get("/interview/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "llm_available" in data
        assert "supported_types" in data
        assert "supported_difficulties" in data

        # Verify supported types
        expected_types = ["behavioral", "technical", "system_design", "case_study", "situational", "competency"]
        for t in expected_types:
            assert t in data["supported_types"]

        # Verify supported difficulties
        expected_difficulties = ["entry", "mid", "senior", "lead", "executive"]
        for d in expected_difficulties:
            assert d in data["supported_difficulties"]
