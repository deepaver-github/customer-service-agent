from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import CurrentUserResponse, LoginRequest, LoginResponse
from app.auth.dependencies import _extract_bearer, current_user
from app.auth.passwords import verify_password
from app.auth.tokens import issue_token, revoke_token
from app.memory.database import get_db
from app.memory.models import Participant, Staff, User

router = APIRouter()


async def _hydrate_name(db: AsyncSession, user: User) -> str | None:
    if user.staff_id:
        row = await db.get(Staff, user.staff_id)
        if row is not None:
            return f"{row.first_name} {row.last_name}"
    if user.participant_id:
        row = await db.get(Participant, user.participant_id)
        if row is not None:
            return f"{row.preferred_name or row.first_name} {row.last_name}"
    return None


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    email = (payload.email or "").strip().lower()
    if not email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password required.")

    stmt = select(User).where(
        User.email == email,
        User.is_active.is_(True),
        User.deleted_at.is_(None),
    )
    user = (await db.execute(stmt)).scalar_one_or_none()

    # Constant-time-ish: always run verify against the stored hash or a dummy
    # so the response timing doesn't leak whether the email exists.
    stored_hash = user.password_hash if user is not None else (
        "scrypt$16384$8$1$" + "0" * 32 + "$" + "0" * 64
    )
    valid = verify_password(payload.password, stored_hash)

    if user is None or not valid:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user.last_login_at = datetime.now(timezone.utc)
    session = await issue_token(db, user)

    return LoginResponse(
        token=session.token,
        expires_at=session.expires_at,
        user=CurrentUserResponse(
            id=user.id,
            email=user.email,
            role=user.role.value,
            staff_id=user.staff_id,
            participant_id=user.participant_id,
            name=await _hydrate_name(db, user),
        ),
    )


@router.post("/logout", status_code=204, response_class=Response)
async def logout(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    token = _extract_bearer(authorization)
    if token:
        await revoke_token(db, token)
    return Response(status_code=204)


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        staff_id=user.staff_id,
        participant_id=user.participant_id,
        name=await _hydrate_name(db, user),
    )
