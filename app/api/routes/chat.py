from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_agent_service
from app.api.models import ChatRequest, ChatResponse
from app.agent.service import AgentService
from app.escalation.handler import handle_escalation
from app.memory.database import get_db
from app.config import get_settings

log = structlog.get_logger()
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    agent: AgentService = Depends(get_agent_service),
):
    try:
        result = await agent.process_message(
            db=db,
            message=request.message,
            session_id=request.session_id,
        )

        if result.escalated:
            settings = get_settings()
            await handle_escalation(
                db=db,
                session_id=result.session_id,
                reason=result.escalation_reason or "Unknown",
                webhook_url=settings.escalation_webhook_url,
            )

        return ChatResponse(
            session_id=result.session_id,
            response=result.response,
            escalated=result.escalated,
            tools_used=result.tools_used,
        )
    except Exception as exc:
        log.error("chat_error", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    agent: AgentService = Depends(get_agent_service),
):
    async def event_generator():
        try:
            async for event in agent.process_message_stream(
                db=db,
                message=request.message,
                session_id=request.session_id,
            ):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }
        except Exception as exc:
            log.error("stream_error", error=str(exc))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    return EventSourceResponse(event_generator())
