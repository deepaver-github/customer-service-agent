"""Phase 4 — clinical tables (medications, preferences, incidents) repository
+ tool tests against in-memory SQLite."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.memory import repository as repo
from app.memory.models import (
    Incident,
    IncidentCategory,
    IncidentStatus,
    IncidentType,
    MedicationRecord,
    MedicationRoute,
    MedicationStatus,
    Participant,
    ParticipantPreference,
    ParticipantStatus,
    PreferenceCategory,
    PreferencePriority,
    Staff,
    StaffRole,
)


def _utc(*args, **kwargs):
    return datetime(*args, **kwargs, tzinfo=timezone.utc)


async def _seed_minimum(db):
    participant = Participant(
        ndis_number="430000002",
        first_name="Test",
        last_name="Subject",
        status=ParticipantStatus.ACTIVE,
    )
    staff = Staff(first_name="Staff", last_name="One", role=StaffRole.SUPPORT_WORKER)
    db.add_all([participant, staff])
    await db.flush()
    return participant, staff


async def test_active_medications_excludes_discontinued(db):
    p, _ = await _seed_minimum(db)
    active = MedicationRecord(
        participant_id=p.id,
        medication_name="Med A",
        dose="10mg",
        route=MedicationRoute.ORAL,
        frequency="daily",
        start_date=date(2025, 1, 1),
        status=MedicationStatus.ACTIVE,
    )
    discontinued = MedicationRecord(
        participant_id=p.id,
        medication_name="Med B",
        dose="5mg",
        route=MedicationRoute.ORAL,
        frequency="daily",
        start_date=date(2024, 1, 1),
        status=MedicationStatus.DISCONTINUED,
    )
    db.add_all([active, discontinued])
    await db.flush()

    rows = await repo.get_active_medications(db, p.id)
    names = [r.medication_name for r in rows]
    assert "Med A" in names
    assert "Med B" not in names


async def test_preferences_filtered_by_category(db):
    p, _ = await _seed_minimum(db)
    db.add_all(
        [
            ParticipantPreference(
                participant_id=p.id,
                category=PreferenceCategory.COMMUNICATION,
                priority=PreferencePriority.HIGH,
                detail="SMS preferred",
            ),
            ParticipantPreference(
                participant_id=p.id,
                category=PreferenceCategory.LIKE,
                priority=PreferencePriority.NORMAL,
                detail="Strong tea",
            ),
        ]
    )
    await db.flush()

    all_prefs = await repo.get_preferences(db, p.id)
    assert len(all_prefs) == 2

    comms = await repo.get_preferences(db, p.id, category=PreferenceCategory.COMMUNICATION)
    assert len(comms) == 1
    assert comms[0].detail == "SMS preferred"


async def test_open_incidents_excludes_closed(db):
    p, s = await _seed_minimum(db)
    closed = Incident(
        participant_id=p.id,
        reporter_staff_id=s.id,
        incident_type=IncidentType.GENERAL,
        category=IncidentCategory.NEAR_MISS,
        occurred_at=_utc(2026, 5, 1, 10),
        summary="Closed event",
        description="...",
        status=IncidentStatus.CLOSED,
    )
    open_inc = Incident(
        participant_id=p.id,
        reporter_staff_id=s.id,
        incident_type=IncidentType.GENERAL,
        category=IncidentCategory.BEHAVIOUR_CONCERN,
        occurred_at=_utc(2026, 5, 20, 10),
        summary="Open event",
        description="...",
        status=IncidentStatus.OPEN,
    )
    db.add_all([closed, open_inc])
    await db.flush()

    rows = await repo.get_open_incidents_for_participant(db, p.id)
    assert len(rows) == 1
    assert rows[0].summary == "Open event"


async def test_get_medications_tool(db):
    from app.tools.examples.get_medications import get_medications as tool

    p, _ = await _seed_minimum(db)
    db.add(
        MedicationRecord(
            participant_id=p.id,
            medication_name="Baclofen",
            dose="10mg",
            route=MedicationRoute.ORAL,
            frequency="3x daily",
            start_date=date(2025, 1, 1),
            status=MedicationStatus.ACTIVE,
        )
    )
    await db.flush()

    out = await tool(db, participant_id=p.id)
    assert len(out["medications"]) == 1
    assert out["medications"][0]["name"] == "Baclofen"


async def test_get_preferences_tool_unknown_category(db):
    from app.tools.examples.get_preferences import get_preferences as tool

    p, _ = await _seed_minimum(db)
    out = await tool(db, participant_id=p.id, category="not_a_real_category")
    assert "error" in out
