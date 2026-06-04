"""Auth — password hashing, token issuance/validation, /auth route round-trip,
and gating + role scoping on participant routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes import auth as auth_routes
from app.api.routes import participants as participants_routes
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import get_user_by_token, issue_token, revoke_token
from app.memory.database import get_db
from app.memory.models import (
    Base,
    Participant,
    ParticipantStatus,
    Staff,
    StaffRole,
    User,
    UserRole,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_hash_and_verify_password_round_trip():
    encoded = hash_password("hunter2!")
    assert encoded.startswith("scrypt$")
    assert verify_password("hunter2!", encoded) is True


def test_verify_rejects_wrong_password():
    encoded = hash_password("correct")
    assert verify_password("wrong", encoded) is False


def test_verify_rejects_garbage_encoded():
    assert verify_password("anything", "") is False
    assert verify_password("anything", "not-a-scrypt-hash") is False


# ---------------------------------------------------------------------------
# Token issue / validate / revoke against in-memory SQLite
# ---------------------------------------------------------------------------


async def _make_user(db) -> User:
    user = User(
        email="t@example.com",
        password_hash=hash_password("pw"),
        role=UserRole.SUPPORT_WORKER,
    )
    db.add(user)
    await db.flush()
    return user


async def test_token_issue_and_lookup(db):
    user = await _make_user(db)
    session = await issue_token(db, user)
    assert session.token
    # SQLite returns naive datetimes; just confirm the token is fresh-ish (10 min window).
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exp = session.expires_at if session.expires_at.tzinfo is None else \
        session.expires_at.astimezone(timezone.utc).replace(tzinfo=None)
    assert exp > now + timedelta(minutes=10)

    resolved = await get_user_by_token(db, session.token)
    assert resolved is not None
    assert resolved.id == user.id


async def test_token_lookup_unknown_returns_none(db):
    assert await get_user_by_token(db, "not-a-real-token") is None
    assert await get_user_by_token(db, "") is None


async def test_token_revoke_invalidates(db):
    user = await _make_user(db)
    session = await issue_token(db, user)
    revoked = await revoke_token(db, session.token)
    assert revoked is True

    resolved = await get_user_by_token(db, session.token)
    assert resolved is None


async def test_expired_token_rejected(db):
    user = await _make_user(db)
    session = await issue_token(db, user, ttl=timedelta(seconds=-1))
    resolved = await get_user_by_token(db, session.token)
    assert resolved is None


# ---------------------------------------------------------------------------
# Full HTTP round-trip with FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def app_db_factory():
    """Spin up a fresh in-memory DB + sessionmaker per HTTP test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed: a staff user, a participant + matching participant user.
    aisha = Participant(
        ndis_number="430999999",
        first_name="A",
        last_name="P",
        status=ParticipantStatus.ACTIVE,
    )
    other = Participant(
        ndis_number="430999998",
        first_name="O",
        last_name="P",
        status=ParticipantStatus.ACTIVE,
    )
    maria = Staff(first_name="M", last_name="L", role=StaffRole.COORDINATOR)
    async with factory() as s:
        s.add_all([aisha, other, maria])
        await s.flush()
        staff_user = User(
            email="maria@example.test",
            password_hash=hash_password("pw1234"),
            role=UserRole.COORDINATOR,
            staff_id=maria.id,
        )
        participant_user = User(
            email="aisha@example.test",
            password_hash=hash_password("pw5678"),
            role=UserRole.PARTICIPANT,
            participant_id=aisha.id,
        )
        s.add_all([staff_user, participant_user])
        await s.commit()
        aisha_id = aisha.id
        other_id = other.id

    yield factory, aisha_id, other_id

    await engine.dispose()


def _make_app(factory) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/auth")
    app.include_router(participants_routes.router, prefix="/participants")

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return app


async def test_login_success(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        r = client.post(
            "/auth/login", json={"email": "maria@example.test", "password": "pw1234"}
        )
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert body["user"]["role"] == "coordinator"


async def test_login_wrong_password(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        r = client.post(
            "/auth/login", json={"email": "maria@example.test", "password": "nope"}
        )
        assert r.status_code == 401


async def test_login_unknown_email(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        r = client.post(
            "/auth/login", json={"email": "nobody@example.test", "password": "pw1234"}
        )
        assert r.status_code == 401


async def test_protected_route_requires_token(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        assert client.get("/participants").status_code == 401


async def test_staff_can_list_participants(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        login = client.post(
            "/auth/login", json={"email": "maria@example.test", "password": "pw1234"}
        ).json()
        r = client.get(
            "/participants",
            headers={"Authorization": f"Bearer {login['token']}"},
        )
        assert r.status_code == 200


async def test_participant_cannot_list_participants(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        login = client.post(
            "/auth/login", json={"email": "aisha@example.test", "password": "pw5678"}
        ).json()
        r = client.get(
            "/participants",
            headers={"Authorization": f"Bearer {login['token']}"},
        )
        # current_staff dependency rejects participant role with 403.
        assert r.status_code == 403


async def test_participant_can_see_own_record(app_db_factory):
    factory, aisha_id, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        login = client.post(
            "/auth/login", json={"email": "aisha@example.test", "password": "pw5678"}
        ).json()
        r = client.get(
            f"/participants/{aisha_id}",
            headers={"Authorization": f"Bearer {login['token']}"},
        )
        assert r.status_code == 200


async def test_participant_cannot_see_other_record(app_db_factory):
    factory, _, other_id = app_db_factory
    with TestClient(_make_app(factory)) as client:
        login = client.post(
            "/auth/login", json={"email": "aisha@example.test", "password": "pw5678"}
        ).json()
        r = client.get(
            f"/participants/{other_id}",
            headers={"Authorization": f"Bearer {login['token']}"},
        )
        assert r.status_code == 403


async def test_logout_revokes_token(app_db_factory):
    factory, _, _ = app_db_factory
    with TestClient(_make_app(factory)) as client:
        login = client.post(
            "/auth/login", json={"email": "maria@example.test", "password": "pw1234"}
        ).json()
        token = login["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Logout
        assert client.post("/auth/logout", headers=headers).status_code == 204

        # Now the token must be rejected.
        assert client.get("/participants", headers=headers).status_code == 401
