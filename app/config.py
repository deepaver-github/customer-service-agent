from __future__ import annotations

import yaml
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


def _encode_userinfo(url: str) -> str:
    """URL-encode the user:password portion of a postgres URL. Railway's
    auto-generated passwords often contain unescaped @ / : % which break
    SQLAlchemy's URL parser. Uses the LAST @ as the userinfo/host boundary,
    so passwords containing @ are handled correctly."""
    scheme, sep, rest = url.partition("://")
    if not sep or "@" not in rest:
        return url
    userinfo, _, hostpart = rest.rpartition("@")
    if ":" not in userinfo:
        return url
    user, _, password = userinfo.partition(":")
    return f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}@{hostpart}"


def _sanitize_for_log(url: str) -> str:
    scheme, sep, rest = url.partition("://")
    if not sep or "@" not in rest:
        return url
    userinfo, _, hostpart = rest.rpartition("@")
    if ":" in userinfo:
        user, _, _ = userinfo.partition(":")
        return f"{scheme}://{user}:***@{hostpart}"
    return f"{scheme}://***@{hostpart}"


class Settings(BaseSettings):
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./agent.db", alias="DATABASE_URL"
    )

    @field_validator("database_url")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        if not v or "${{" in v:
            raise ValueError(
                f"DATABASE_URL is empty or contains an unresolved template: {v!r}. "
                "Check the variable reference in Railway's Variables tab."
            )
        # Heroku/Railway expose postgres://; SQLAlchemy 2.x requires postgresql://
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        # asyncpg doesn't understand libpq's sslmode= param; strip/translate it.
        if "sslmode=" in v:
            v = v.replace("sslmode=require", "ssl=true").replace("sslmode=", "ssl=")
        # Re-encode user:password — Railway's auto-generated passwords often
        # contain @ / : % which SQLAlchemy can't parse unless they're encoded.
        if v.startswith("postgresql+asyncpg://"):
            v = _encode_userinfo(v)
        print(f"[config] DATABASE_URL resolved to: {_sanitize_for_log(v)}", flush=True)
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
