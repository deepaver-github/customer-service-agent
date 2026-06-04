"""FastAPI auth dependencies and role helpers."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import get_user_by_token
from app.memory.database import get_db
from app.memory.models import STAFF_ROLES, User, UserRole


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user_by_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def current_staff(user: User = Depends(current_user)) -> User:
    if user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is restricted to staff members.",
        )
    return user


def participant_can_access(user: User, participant_id: str) -> bool:
    """Staff see everyone; participants see only their own record."""
    if user.role in STAFF_ROLES:
        return True
    if user.role == UserRole.PARTICIPANT and user.participant_id == participant_id:
        return True
    return False
