"""Phase 4 — immutability triggers on progress_notes + medication_administration_log.

These triggers are Postgres-only (PL/pgSQL), so the tests are skipped unless
a TEST_DATABASE_URL pointing at a real Postgres instance is set in the env.
Run with::

    TEST_DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/cs_test \
        pytest tests/test_immutability.py -v
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.memory.database import (
    AUDIT_FUNCTION_SQL,
    AUDITED_TABLES,
    MED_ADMIN_IMMUTABILITY_SQL,
    MED_ADMIN_IMMUTABILITY_TRIGGER_SQL,
    PROGRESS_NOTE_IMMUTABILITY_SQL,
    PROGRESS_NOTE_IMMUTABILITY_TRIGGER_SQL,
    _trigger_sql,
)
from app.memory.models import (
    Base,
    MedicationAdministrationLog,
    MedicationRecord,
    MedicationRoute,
    Participant,
    ParticipantStatus,
    ProgressNote,
    ProgressNoteType,
    Staff,
    StaffRole,
)
from sqlalchemy import text


pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="Immutability triggers are Postgres-only; set TEST_DATABASE_URL to run.",
)


@pytest_asyncio.fixture
async def pg_db():
    url = os.environ["TEST_DATABASE_URL"]
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(AUDIT_FUNCTION_SQL))
        for table in AUDITED_TABLES:
            await conn.execute(text(_trigger_sql(table)))
        await conn.execute(text(PROGRESS_NOTE_IMMUTABILITY_SQL))
        await conn.execute(text(PROGRESS_NOTE_IMMUTABILITY_TRIGGER_SQL))
        await conn.execute(text(MED_ADMIN_IMMUTABILITY_SQL))
        await conn.execute(text(MED_ADMIN_IMMUTABILITY_TRIGGER_SQL))

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


async def _make_people(db):
    p = Participant(
        ndis_number="430000099",
        first_name="Test",
        last_name="P",
        status=ParticipantStatus.ACTIVE,
    )
    s = Staff(first_name="T", last_name="S", role=StaffRole.SUPPORT_WORKER)
    db.add_all([p, s])
    await db.flush()
    return p, s


async def test_unlocked_progress_note_can_be_edited(pg_db):
    p, s = await _make_people(pg_db)
    note = ProgressNote(
        participant_id=p.id,
        author_staff_id=s.id,
        note_type=ProgressNoteType.SHIFT_NOTE,
        content="initial",
    )
    pg_db.add(note)
    await pg_db.commit()

    note.content = "edited while unlocked"
    await pg_db.commit()  # should succeed


async def test_locked_progress_note_cannot_be_updated(pg_db):
    p, s = await _make_people(pg_db)
    note = ProgressNote(
        participant_id=p.id,
        author_staff_id=s.id,
        note_type=ProgressNoteType.SHIFT_NOTE,
        content="initial",
        locked_at=datetime.now(timezone.utc),
        locked_by_staff_id=s.id,
    )
    pg_db.add(note)
    await pg_db.commit()

    note.content = "trying to edit a locked note"
    with pytest.raises(DBAPIError):
        await pg_db.commit()


async def test_med_admin_log_is_immutable(pg_db):
    p, s = await _make_people(pg_db)
    med = MedicationRecord(
        participant_id=p.id,
        medication_name="Test",
        dose="1mg",
        route=MedicationRoute.ORAL,
        frequency="daily",
        start_date=date(2025, 1, 1),
    )
    pg_db.add(med)
    await pg_db.flush()
    entry = MedicationAdministrationLog(
        medication_record_id=med.id,
        participant_id=p.id,
        administered_by_staff_id=s.id,
        administered_at=datetime.now(timezone.utc),
        dose_given="1mg",
    )
    pg_db.add(entry)
    await pg_db.commit()

    entry.notes = "edit attempt"
    with pytest.raises(DBAPIError):
        await pg_db.commit()
