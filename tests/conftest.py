from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.memory.models import Base

import app.tools.examples  # noqa: F401
import app.escalation.handler  # noqa: F401


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def agent_config():
    return {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
        "max_tool_iterations": 10,
        "personality": "You are a helpful test agent.",
        "enabled_tools": ["lookup_order", "get_account_info", "search_faq", "escalate"],
        "memory": {"max_context_tokens": 50000, "max_recent_messages": 40},
        "escalation": {"max_turns_before_escalate": 5},
    }


@pytest.fixture
def mock_anthropic_client():
    client = AsyncMock()
    return client


def make_text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    return response


def make_tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tu_123"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id

    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    return response


# --- Streaming mock helpers ---

import json


class MockStreamEvent:
    def __init__(self, type, **kwargs):
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)


def make_text_stream_events(text: str, stop_reason: str = "end_turn"):
    events = []

    cb_start = MockStreamEvent("content_block_start")
    cb_start.content_block = MagicMock(type="text", text="")
    events.append(cb_start)

    words = text.split(" ")
    for i, word in enumerate(words):
        delta_text = word if i == 0 else " " + word
        delta = MockStreamEvent("content_block_delta")
        delta.delta = MagicMock(type="text_delta", text=delta_text)
        events.append(delta)

    events.append(MockStreamEvent("content_block_stop"))

    msg_delta = MockStreamEvent("message_delta")
    msg_delta.delta = MagicMock(stop_reason=stop_reason)
    events.append(msg_delta)

    return events


def make_tool_use_stream_events(
    tool_name: str, tool_input: dict, tool_use_id: str = "tu_123"
):
    events = []

    cb_start = MockStreamEvent("content_block_start")
    content_block = MagicMock(type="tool_use", id=tool_use_id)
    content_block.name = tool_name
    cb_start.content_block = content_block
    events.append(cb_start)

    input_json = json.dumps(tool_input)
    delta = MockStreamEvent("content_block_delta")
    delta.delta = MagicMock(type="input_json_delta", partial_json=input_json)
    events.append(delta)

    events.append(MockStreamEvent("content_block_stop"))

    msg_delta = MockStreamEvent("message_delta")
    msg_delta.delta = MagicMock(stop_reason="tool_use")
    events.append(msg_delta)

    return events


class MockAsyncStream:
    def __init__(self, events, final_message):
        self._events = events
        self._final_message = final_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for event in self._events:
            yield event

    def get_final_message(self):
        return self._final_message
