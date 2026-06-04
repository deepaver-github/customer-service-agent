from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import current_staff, current_user
from app.main import app
from app.memory.database import init_db
from app.memory.models import User, UserRole


def _fake_staff_user() -> User:
    return User(
        id="00000000-0000-0000-0000-000000000001",
        email="test-staff@example.test",
        password_hash="x",
        role=UserRole.COORDINATOR,
    )


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db("sqlite+aiosqlite:///:memory:")
    # Bypass auth in chat-API regression tests — they predate auth.
    app.dependency_overrides[current_user] = lambda: _fake_staff_user()
    app.dependency_overrides[current_staff] = lambda: _fake_staff_user()
    yield
    app.dependency_overrides.pop(current_user, None)
    app.dependency_overrides.pop(current_staff, None)


class TestChatAPI:
    async def test_health_check(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    async def test_create_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "active"

    async def test_get_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post("/sessions", json={})
            session_id = create_resp.json()["id"]

            get_resp = await client.get(f"/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == session_id

    async def test_get_session_not_found(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sessions/nonexistent-id")
        assert response.status_code == 404

    async def test_delete_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post("/sessions", json={})
            session_id = create_resp.json()["id"]

            delete_resp = await client.delete(f"/sessions/{session_id}")
        assert delete_resp.status_code == 204

    async def test_list_sessions_empty(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sessions")
        assert response.status_code == 200
        assert response.json() == {"items": [], "next_cursor": None}

    async def test_list_sessions_with_data(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(3):
                await client.post("/sessions", json={})

            response = await client.get("/sessions?limit=2")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2
        assert body["next_cursor"] is not None
        assert all("last_message_preview" in item for item in body["items"])

    async def test_list_sessions_invalid_cursor(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sessions?cursor=garbage")
        assert response.status_code == 400

    async def test_chat_endpoint(self):
        from app.agent.service import AgentResponse
        from app.api.dependencies import get_agent_service

        mock_service = AsyncMock()
        mock_service.process_message.return_value = AgentResponse(
            session_id="test-session",
            response="Hello! How can I help?",
            escalated=False,
            tools_used=[],
        )

        app.dependency_overrides[get_agent_service] = lambda: mock_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/chat",
                    json={"message": "Hi"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Hello! How can I help?"
            assert data["escalated"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_chat_stream_endpoint(self):
        from app.api.dependencies import get_agent_service

        async def fake_stream(db, message, session_id=None, user_id=None):
            yield {"event": "stream_start", "data": {"session_id": "test-session"}}
            yield {"event": "text_delta", "data": {"delta": "Hello"}}
            yield {"event": "done", "data": {"response": "Hello", "session_id": "test-session", "escalated": False, "tools_used": []}}

        mock_service = AsyncMock()
        mock_service.process_message_stream = fake_stream

        app.dependency_overrides[get_agent_service] = lambda: mock_service

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/chat/stream",
                    json={"message": "Hi"},
                )

            assert response.status_code == 200
            body = response.text
            assert "stream_start" in body
            assert "text_delta" in body
            assert "done" in body
        finally:
            app.dependency_overrides.clear()
