from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory.models import Message, Session, SessionStatus


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
