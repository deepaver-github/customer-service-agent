from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.memory.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db("sqlite+aiosqlite:///:memory:")


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
