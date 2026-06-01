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
    participant_id: str | None = Field(
        default=None,
        description="Optional Special Care Australia participant id this session is on behalf of",
    )
    staff_id: str | None = Field(
        default=None,
        description="Optional staff id if a staff member is using the assistant",
    )


class SessionResponse(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: dict | None = None
    participant_id: str | None = None
    staff_id: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | dict | list
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class SessionListItem(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    items: list[SessionListItem] = Field(default_factory=list)
    next_cursor: str | None = None


class ErrorResponse(BaseModel):
    error: str
    code: str
