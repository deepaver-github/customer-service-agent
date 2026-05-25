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
