from __future__ import annotations

from functools import lru_cache

import anthropic

from app.agent.service import AgentService
from app.config import get_settings, get_agent_config
import app.tools.examples  # noqa: F401 — registers tools on import


@lru_cache
def get_agent_service() -> AgentService:
    settings = get_settings()
    agent_config = get_agent_config()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return AgentService(client=client, agent_config=agent_config)
