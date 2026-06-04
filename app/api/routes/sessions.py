from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    MessageResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionListItem,
    SessionListResponse,
    SessionResponse,
)
from app.auth.dependencies import current_user
from app.memory import repository as repo
from app.memory.database import get_db
from app.memory.models import STAFF_ROLES, SessionStatus, User, UserRole

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: SessionCreate | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    metadata = request.metadata if request else None
    participant_id = request.participant_id if request else None
    staff_id = request.staff_id if request else None

    # Participant users can only create sessions for themselves; staff can
    # create on behalf of any participant. Auto-fill staff_id from the user
    # when they're a team member.
    if user.role == UserRole.PARTICIPANT:
        if participant_id and participant_id != user.participant_id:
            raise HTTPException(
                status_code=403, detail="Participants can only chat about themselves."
            )
        participant_id = user.participant_id
    elif user.role in STAFF_ROLES and staff_id is None and user.staff_id:
        staff_id = user.staff_id

    session = await repo.create_session(
        db,
        metadata=metadata,
        participant_id=participant_id,
        staff_id=staff_id,
        user_id=user.id,
    )
    return SessionResponse(
        id=session.id,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        metadata=session.metadata_,
        participant_id=session.participant_id,
        staff_id=session.staff_id,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """Return chat sessions the caller is allowed to see.

    Everyone sees the sessions they created. Admins additionally see any
    session whose status is ``escalated`` (cross-user oversight) — but only
    that subset; non-escalated sessions belonging to other users stay hidden.
    """
    try:
        items, next_cursor = await repo.list_sessions(
            db,
            cursor=cursor,
            limit=limit,
            user_id=user.id,
            include_escalated=(user.role == UserRole.ADMIN),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SessionListResponse(
        items=[SessionListItem(**item) for item in items],
        next_cursor=next_cursor,
    )


def _can_view_session(user: User, session) -> bool:
    if session.user_id == user.id:
        return True
    if user.role == UserRole.ADMIN and session.status == SessionStatus.ESCALATED:
        return True
    return False


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    session = await repo.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _can_view_session(user, session):
        raise HTTPException(status_code=403, detail="Not your session.")

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
        participant_id=session.participant_id,
        staff_id=session.staff_id,
        messages=messages,
    )


@router.delete("/{session_id}", status_code=204)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    existing = await repo.get_session(db, session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if existing.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your session.")
    await repo.update_session_status(db, session_id, SessionStatus.CLOSED)
