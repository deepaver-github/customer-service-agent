from __future__ import annotations

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.memory.models import SessionStatus
from app.tools.registry import register_tool

log = structlog.get_logger()


@register_tool(
    name="escalate",
    description="Escalate the conversation to a human agent. Use this when the customer explicitly requests a human, is very frustrated, or the issue cannot be resolved. Provide a clear reason for the escalation.",
)
def escalate(reason: str) -> dict:
    return {"status": "escalated", "reason": reason}


async def handle_escalation(
    db: AsyncSession,
    session_id: str,
    reason: str,
    webhook_url: str | None = None,
) -> None:
    await repo.update_session_status(db, session_id, SessionStatus.ESCALATED)

    messages = await repo.get_messages(db, session_id)
    message_count = len(messages)

    summary = ""
    for msg in messages[-5:]:
        content = msg.content
        if isinstance(content, str):
            summary += f"{msg.role}: {content[:200]}\n"

    payload = {
        "session_id": session_id,
        "reason": reason,
        "summary": summary.strip(),
        "messages_count": message_count,
    }

    if webhook_url:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                log.info(
                    "escalation_webhook_sent",
                    session_id=session_id,
                    status_code=response.status_code,
                )
        except Exception as exc:
            log.error(
                "escalation_webhook_failed",
                session_id=session_id,
                error=str(exc),
            )
    else:
        log.info(
            "escalation_logged",
            session_id=session_id,
            reason=reason,
            payload=payload,
        )
