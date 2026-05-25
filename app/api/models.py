from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Existing session ID to continue a conversation")
    message: str = Field(description="The user's message")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    escalated: bool = False
    tools_used: list[str] = Field(default_factory=list)


class SessionCreate(BaseModel):
    metadata: dict | None = Field(default=None, description="Optional session metadata")


class SessionResponse(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: dict | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | dict | list
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: str
    code: str
