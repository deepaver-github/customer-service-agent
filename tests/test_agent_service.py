from __future__ import annotations

from unittest.mock import MagicMock

from tests.conftest import (
    make_text_response,
    make_tool_use_response,
    make_text_stream_events,
    make_tool_use_stream_events,
    MockAsyncStream,
)
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


class TestAgentServiceStreaming:
    async def _collect_events(self, stream):
        events = []
        async for event in stream:
            events.append(event)
        return events

    async def test_stream_simple_text_response(
        self, db, agent_config, mock_anthropic_client
    ):
        text = "Hello! How can I help you today?"
        stream_events = make_text_stream_events(text)
        final_msg = make_text_response(text)

        mock_anthropic_client.messages.stream = MagicMock(
            return_value=MockAsyncStream(stream_events, final_msg)
        )
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        events = await self._collect_events(
            agent.process_message_stream(db, "Hi there")
        )

        event_types = [e["event"] for e in events]
        assert event_types[0] == "stream_start"
        assert "text_delta" in event_types
        assert event_types[-1] == "done"

        done_data = events[-1]["data"]
        assert done_data["response"] == text
        assert done_data["escalated"] is False
        assert done_data["tools_used"] == []

    async def test_stream_tool_use_flow(
        self, db, agent_config, mock_anthropic_client
    ):
        tool_events = make_tool_use_stream_events(
            "lookup_order", {"order_id": "ORD-1234"}, tool_use_id="tu_456"
        )
        tool_final = make_tool_use_response(
            "lookup_order", {"order_id": "ORD-1234"}, tool_use_id="tu_456"
        )

        answer = "Your order ORD-1234 has been shipped!"
        text_events = make_text_stream_events(answer)
        text_final = make_text_response(answer)

        mock_anthropic_client.messages.stream = MagicMock(
            side_effect=[
                MockAsyncStream(tool_events, tool_final),
                MockAsyncStream(text_events, text_final),
            ]
        )
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        events = await self._collect_events(
            agent.process_message_stream(db, "Where is my order ORD-1234?")
        )

        event_types = [e["event"] for e in events]
        assert "tool_start" in event_types
        assert "tool_result" in event_types
        assert "text_delta" in event_types
        assert event_types[-1] == "done"

        tool_start = next(e for e in events if e["event"] == "tool_start")
        assert tool_start["data"]["tool_name"] == "lookup_order"

        done_data = events[-1]["data"]
        assert "lookup_order" in done_data["tools_used"]
        assert done_data["response"] == answer

    async def test_stream_escalation_flow(
        self, db, agent_config, mock_anthropic_client
    ):
        esc_events = make_tool_use_stream_events(
            "escalate", {"reason": "Customer wants human"}, tool_use_id="tu_esc"
        )
        esc_final = make_tool_use_response(
            "escalate", {"reason": "Customer wants human"}, tool_use_id="tu_esc"
        )

        answer = "I'm connecting you with a team member."
        text_events = make_text_stream_events(answer)
        text_final = make_text_response(answer)

        mock_anthropic_client.messages.stream = MagicMock(
            side_effect=[
                MockAsyncStream(esc_events, esc_final),
                MockAsyncStream(text_events, text_final),
            ]
        )
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        events = await self._collect_events(
            agent.process_message_stream(db, "I want a human")
        )

        event_types = [e["event"] for e in events]
        assert "escalation" in event_types
        assert events[-1]["data"]["escalated"] is True
        assert "escalate" in events[-1]["data"]["tools_used"]

    async def test_stream_db_persistence(
        self, db, agent_config, mock_anthropic_client
    ):
        from app.memory import repository as repo

        text = "Saved to DB"
        stream_events = make_text_stream_events(text)
        final_msg = make_text_response(text)

        mock_anthropic_client.messages.stream = MagicMock(
            return_value=MockAsyncStream(stream_events, final_msg)
        )
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        events = await self._collect_events(
            agent.process_message_stream(db, "Test persistence")
        )

        session_id = events[0]["data"]["session_id"]
        messages = await repo.get_messages(db, session_id)
        roles = [m.role for m in messages]
        assert "user" in roles
        assert "assistant" in roles
        assistant_msg = next(m for m in messages if m.role == "assistant")
        assert assistant_msg.content == text

    async def test_stream_error_handling(
        self, db, agent_config, mock_anthropic_client
    ):
        mock_anthropic_client.messages.stream = MagicMock(
            side_effect=Exception("API connection failed")
        )
        agent = AgentService(client=mock_anthropic_client, agent_config=agent_config)

        events = await self._collect_events(
            agent.process_message_stream(db, "This will fail")
        )

        event_types = [e["event"] for e in events]
        assert "stream_start" in event_types
        assert "error" in event_types
        error_event = next(e for e in events if e["event"] == "error")
        assert "API connection failed" in error_event["data"]["error"]
