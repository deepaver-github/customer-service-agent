from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    MessageResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
)
from app.memory import repository as repo
from app.memory.database import get_db
from app.memory.models import SessionStatus

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: SessionCreate | None = None,
    db: AsyncSession = Depends(get_db),
):
    metadata = request.metadata if request else None
    session = await repo.create_session(db, metadata=metadata)
    return SessionResponse(
        id=session.id,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        metadata=session.metadata_,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await repo.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in session.messages
    ]

    return SessionDetailResponse(
        id=session.id,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        metadata=session.metadata_,
        messages=messages,
    )


@router.delete("/{session_id}", status_code=204)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await repo.update_session_status(db, session_id, SessionStatus.CLOSED)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
