from __future__ import annotations

import yaml
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./agent.db", alias="DATABASE_URL"
    )

    @field_validator("database_url")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    escalation_webhook_url: str | None = Field(
        default=None, alias="ESCALATION_WEBHOOK_URL"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_agent_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).parent.parent / "agent_config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)["agent"]


@lru_cache
def get_agent_config() -> dict[str, Any]:
    return load_agent_config()
