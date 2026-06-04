"""Phase 3 — shifts repository + tool tests against in-memory SQLite."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.memory import repository as repo
from app.memory.models import (
    Participant,
    ParticipantStatus,
    ServiceType,
    Shift,
    ShiftStatus,
    Staff,
    StaffRole,
)


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


async def _seed_minimum(db):
    participant = Participant(
        ndis_number="430000001",
        first_name="Test",
        last_name="Person",
        status=ParticipantStatus.ACTIVE,
    )
    staff = Staff(
        first_name="Worker",
        last_name="One",
        role=StaffRole.SUPPORT_WORKER,
    )
    svc = ServiceType(code="personal_care_test", name="Personal Care (test)")
    db.add_all([participant, staff, svc])
    await db.flush()
    return participant, staff, svc


async def test_upcoming_shifts_returns_future_scheduled_only(db):
    participant, staff, svc = await _seed_minimum(db)

    now = datetime.now(timezone.utc)
    past = Shift(
        participant_id=participant.id,
        staff_id=staff.id,
        service_type_id=svc.id,
        scheduled_start=now - timedelta(days=2),
        scheduled_end=now - timedelta(days=2, hours=-2),
        status=ShiftStatus.COMPLETED,
    )
    future = Shift(
        participant_id=participant.id,
        staff_id=staff.id,
        service_type_id=svc.id,
        scheduled_start=now + timedelta(days=1),
        scheduled_end=now + timedelta(days=1, hours=2),
        status=ShiftStatus.SCHEDULED,
    )
    db.add_all([past, future])
    await db.flush()

    rows = await repo.get_upcoming_shifts(db, participant.id)
    assert len(rows) == 1
    assert rows[0][0].id == future.id


async def test_recent_shifts_excludes_scheduled(db):
    participant, staff, svc = await _seed_minimum(db)

    now = datetime.now(timezone.utc)
    scheduled = Shift(
        participant_id=participant.id,
        staff_id=staff.id,
        service_type_id=svc.id,
        scheduled_start=now + timedelta(days=1),
        scheduled_end=now + timedelta(days=1, hours=2),
        status=ShiftStatus.SCHEDULED,
    )
    completed = Shift(
        participant_id=participant.id,
        staff_id=staff.id,
        service_type_id=svc.id,
        scheduled_start=now - timedelta(days=2),
        scheduled_end=now - timedelta(days=2, hours=-2),
        status=ShiftStatus.COMPLETED,
    )
    no_show = Shift(
        participant_id=participant.id,
        staff_id=staff.id,
        service_type_id=svc.id,
        scheduled_start=now - timedelta(days=4),
        scheduled_end=now - timedelta(days=4, hours=-2),
        status=ShiftStatus.NO_SHOW,
    )
    db.add_all([scheduled, completed, no_show])
    await db.flush()

    rows = await repo.get_recent_shifts(db, participant.id)
    statuses = {row[0].status for row in rows}
    assert ShiftStatus.SCHEDULED not in statuses
    assert ShiftStatus.COMPLETED in statuses
    assert ShiftStatus.NO_SHOW in statuses


async def test_get_upcoming_shifts_tool(db):
    from app.tools.examples.get_upcoming_shifts import get_upcoming_shifts as tool

    participant, staff, svc = await _seed_minimum(db)
    now = datetime.now(timezone.utc)
    db.add(
        Shift(
            participant_id=participant.id,
            staff_id=staff.id,
            service_type_id=svc.id,
            scheduled_start=now + timedelta(hours=4),
            scheduled_end=now + timedelta(hours=6),
            status=ShiftStatus.SCHEDULED,
            location="Test Address",
        )
    )
    await db.flush()

    result = await tool(db, participant_id=participant.id)
    assert "upcoming_shifts" in result
    assert len(result["upcoming_shifts"]) == 1
    assert result["upcoming_shifts"][0]["location"] == "Test Address"
    assert result["upcoming_shifts"][0]["support_worker"] == "Worker One"


async def test_get_upcoming_shifts_tool_unknown_participant(db):
    from app.tools.examples.get_upcoming_shifts import get_upcoming_shifts as tool

    result = await tool(db, participant_id="00000000-0000-0000-0000-000000000000")
    assert "error" in result
