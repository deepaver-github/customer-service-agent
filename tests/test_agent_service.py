from __future__ import annotations

from tests.conftest import make_text_response, make_tool_use_response
from app.agent.service import AgentService


class TestAgentService:
    async def test_simple_text_response(self, db, agent_config, mock_anthropic_client):
        mock_anthropic_client.messages.create.return_value = make_text_response(
            "Hello! How can I help you today?"
        )
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        result = await agent.process_message(db, "Hi there")

        assert result.session_id is not None
        assert result.response == "Hello! How can I help you today?"
        assert result.escalated is False
        assert result.tools_used == []

    async def test_tool_use_flow(self, db, agent_config, mock_anthropic_client):
        tool_response = make_tool_use_response(
            "lookup_order", {"order_id": "ORD-1234"}
        )
        text_response = make_text_response(
            "Your order ORD-1234 has been shipped!"
        )
        mock_anthropic_client.messages.create.side_effect = [
            tool_response,
            text_response,
        ]

        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)
        result = await agent.process_message(db, "Where is my order ORD-1234?")

        assert "lookup_order" in result.tools_used
        assert "shipped" in result.response
        assert mock_anthropic_client.messages.create.call_count == 2

    async def test_escalation_flow(self, db, agent_config, mock_anthropic_client):
        escalate_response = make_tool_use_response(
            "escalate", {"reason": "Customer requested human agent"}
        )
        text_response = make_text_response(
            "I'm connecting you with a team member who can help."
        )
        mock_anthropic_client.messages.create.side_effect = [
            escalate_response,
            text_response,
        ]

        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)
        result = await agent.process_message(db, "I want to talk to a human")

        assert result.escalated is True
        assert result.escalation_reason == "Customer requested human agent"
        assert "escalate" in result.tools_used

    async def test_session_continuity(self, db, agent_config, mock_anthropic_client):
        mock_anthropic_client.messages.create.return_value = make_text_response("Response 1")
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        result1 = await agent.process_message(db, "First message")
        session_id = result1.session_id

        mock_anthropic_client.messages.create.return_value = make_text_response("Response 2")
        result2 = await agent.process_message(db, "Second message", session_id=session_id)

        assert result2.session_id == session_id
