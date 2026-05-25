from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.escalation.handler import handle_escalation, escalate
from app.memory import repository as repo
from app.memory.models import SessionStatus


class TestEscalation:
    def test_escalate_tool_returns_status(self):
        result = escalate(reason="Customer is upset")
        assert result["status"] == "escalated"
        assert result["reason"] == "Customer is upset"

    async def test_handle_escalation_updates_status(self, db):
        session = await repo.create_session(db)
        await repo.add_message(db, session.id, "user", "I need help")

        await handle_escalation(
            db=db,
            session_id=session.id,
            reason="Test escalation",
            webhook_url=None,
        )

        updated = await repo.get_session(db, session.id)
        assert updated.status == SessionStatus.ESCALATED

    async def test_handle_escalation_sends_webhook(self, db):
        session = await repo.create_session(db)
        await repo.add_message(db, session.id, "user", "Help me")

        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("app.escalation.handler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await handle_escalation(
                db=db,
                session_id=session.id,
                reason="Webhook test",
                webhook_url="https://example.com/webhook",
            )

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["session_id"] == session.id
            assert call_args[1]["json"]["reason"] == "Webhook test"

    async def test_handle_escalation_webhook_failure_does_not_raise(self, db):
        session = await repo.create_session(db)

        with patch("app.escalation.handler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await handle_escalation(
                db=db,
                session_id=session.id,
                reason="Failure test",
                webhook_url="https://example.com/webhook",
            )
