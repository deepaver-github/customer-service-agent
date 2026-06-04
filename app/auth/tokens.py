"""Opaque session token issuance, lookup, revocation."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import AuthSession, User

TOKEN_BYTES = 48  # 64-char urlsafe-base64 token
DEFAULT_TTL = timedelta(days=7)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue_token(
    db: AsyncSession, user: User, ttl: timedelta = DEFAULT_TTL
) -> AuthSession:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    session = AuthSession(
        token=token,
        user_id=user.id,
        expires_at=_now() + ttl,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_user_by_token(db: AsyncSession, token: str) -> User | None:
    """Resolve a Bearer token to a live user. Returns None if absent/expired/revoked."""
    if not token:
        return None
    stmt = (
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(
            AuthSession.token == token,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > _now(),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return row[1]


async def revoke_token(db: AsyncSession, token: str) -> bool:
    stmt = (
        update(AuthSession)
        .where(AuthSession.token == token, AuthSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    result = await db.execute(stmt)
    await db.commit()
    return (result.rowcount or 0) > 0
