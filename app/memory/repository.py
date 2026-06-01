from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory.models import Message, Session, SessionStatus

PREVIEW_MAX_LEN = 120


async def create_session(
    db: AsyncSession, metadata: dict | None = None
) -> Session:
    session = Session(metadata_=metadata)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    stmt = (
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.messages))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_session_status(
    db: AsyncSession, session_id: str, status: SessionStatus
) -> Session | None:
    session = await get_session(db, session_id)
    if session is None:
        return None
    session.status = status
    await db.commit()
    await db.refresh(session)
    return session


async def add_message(
    db: AsyncSession, session_id: str, role: str, content: dict | list
) -> Message:
    message = Message(session_id=session_id, role=role, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(
    db: AsyncSession, session_id: str, limit: int | None = None
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_message_count(db: AsyncSession, session_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(Message)
        .where(Message.session_id == session_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


def _extract_preview(content: Any) -> str | None:
    """Reduce a Message.content (str | dict | list) to a short display string."""
    if content is None:
        return None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                elif item.get("type") == "tool_use" and isinstance(item.get("name"), str):
                    text_parts.append(f"[used {item['name']}]")
                elif item.get("type") == "tool_result":
                    text_parts.append("[tool result]")
            elif isinstance(item, str):
                text_parts.append(item)
        text = " ".join(text_parts).strip()
        if not text:
            return None
    elif isinstance(content, dict):
        if isinstance(content.get("text"), str):
            text = content["text"]
        elif content.get("type") == "tool_use" and isinstance(content.get("name"), str):
            text = f"[used {content['name']}]"
        else:
            return None
    else:
        return None

    text = " ".join(text.split())
    if len(text) > PREVIEW_MAX_LEN:
        text = text[: PREVIEW_MAX_LEN - 1].rstrip() + "…"
    return text or None


def _encode_cursor(updated_at: datetime, session_id: str) -> str:
    raw = f"{updated_at.isoformat()}|{session_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        iso, session_id = raw.split("|", 1)
        return datetime.fromisoformat(iso), session_id
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("invalid cursor") from exc


async def list_sessions(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[dict], str | None]:
    """List sessions ordered by updated_at DESC, with cursor pagination.

    Returns (items, next_cursor) where each item is a dict with:
        id, status, created_at, updated_at, last_message_preview, message_count.
    A correlated subquery picks the latest user/assistant message per session in
    one round-trip (no N+1).
    """
    last_msg_subq = (
        select(Message.content)
        .where(Message.session_id == Session.id)
        .where(Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Session)
        .scalar_subquery()
    )

    count_subq = (
        select(func.count(Message.id))
        .where(Message.session_id == Session.id)
        .correlate(Session)
        .scalar_subquery()
    )

    stmt = select(
        Session.id,
        Session.status,
        Session.created_at,
        Session.updated_at,
        last_msg_subq.label("last_content"),
        count_subq.label("message_count"),
    )

    if cursor is not None:
        cursor_updated_at, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Session.updated_at < cursor_updated_at,
                and_(
                    Session.updated_at == cursor_updated_at,
                    Session.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(Session.updated_at.desc(), Session.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    rows = list(result.all())

    has_more = len(rows) > limit
    page = rows[:limit]

    items = [
        {
            "id": row.id,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "last_message_preview": _extract_preview(row.last_content),
            "message_count": row.message_count or 0,
        }
        for row in page
    ]

    next_cursor = (
        _encode_cursor(page[-1].updated_at, page[-1].id) if has_more and page else None
    )

    return items, next_cursor
