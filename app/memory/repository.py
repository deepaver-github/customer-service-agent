from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory.models import (
    AgreementStatus,
    AuditLog,
    Contact,
    Goal,
    GoalStatus,
    Incident,
    IncidentStatus,
    KnowledgeArticle,
    KnowledgeStatus,
    MedicationAdministrationLog,
    MedicationRecord,
    MedicationStatus,
    Message,
    Participant,
    ParticipantPreference,
    ParticipantStaffAssignment,
    ParticipantStatus,
    PreferenceCategory,
    Plan,
    PlanStatus,
    ProgressNote,
    RestrictivePractice,
    RestrictivePracticeStatus,
    RiskAssessment,
    ServiceAgreement,
    ServiceType,
    ServiceTypeStatus,
    Session,
    SessionStatus,
    Shift,
    ShiftStatus,
    Staff,
    StaffStatus,
)

PREVIEW_MAX_LEN = 120


async def create_session(
    db: AsyncSession,
    metadata: dict | None = None,
    participant_id: str | None = None,
    staff_id: str | None = None,
    user_id: str | None = None,
) -> Session:
    session = Session(
        metadata_=metadata,
        participant_id=participant_id,
        staff_id=staff_id,
        user_id=user_id,
    )
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


def _extract_preview(content: Any) -> str | None:
    """Reduce a Message.content (str | dict | list) to a short display string."""
    if content is None:
        return None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                elif item.get("type") == "tool_use" and isinstance(item.get("name"), str):
                    text_parts.append(f"[used {item['name']}]")
                elif item.get("type") == "tool_result":
                    text_parts.append("[tool result]")
            elif isinstance(item, str):
                text_parts.append(item)
        text = " ".join(text_parts).strip()
        if not text:
            return None
    elif isinstance(content, dict):
        if isinstance(content.get("text"), str):
            text = content["text"]
        elif content.get("type") == "tool_use" and isinstance(content.get("name"), str):
            text = f"[used {content['name']}]"
        else:
            return None
    else:
        return None

    text = " ".join(text.split())
    if len(text) > PREVIEW_MAX_LEN:
        text = text[: PREVIEW_MAX_LEN - 1].rstrip() + "…"
    return text or None


def _encode_cursor(updated_at: datetime, session_id: str) -> str:
    raw = f"{updated_at.isoformat()}|{session_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        iso, session_id = raw.split("|", 1)
        return datetime.fromisoformat(iso), session_id
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("invalid cursor") from exc


async def list_sessions(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
    user_id: str | None = None,
    include_escalated: bool = False,
) -> tuple[list[dict], str | None]:
    """List sessions ordered by updated_at DESC, with cursor pagination.

    Returns (items, next_cursor) where each item is a dict with:
        id, status, created_at, updated_at, last_message_preview, message_count.
    A correlated subquery picks the latest user/assistant message per session in
    one round-trip (no N+1).

    Owner scoping:
        - When ``user_id`` is provided, only sessions where ``user_id`` matches
          are returned. If ``include_escalated`` is also True, escalated sessions
          (regardless of owner) are included as well — the admin view.
        - When ``user_id`` is None and ``include_escalated`` is False, no rows
          are returned. Callers must always pass an explicit scope.
    """
    last_msg_subq = (
        select(Message.content)
        .where(Message.session_id == Session.id)
        .where(Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Session)
        .scalar_subquery()
    )

    count_subq = (
        select(func.count(Message.id))
        .where(Message.session_id == Session.id)
        .correlate(Session)
        .scalar_subquery()
    )

    stmt = select(
        Session.id,
        Session.status,
        Session.created_at,
        Session.updated_at,
        last_msg_subq.label("last_content"),
        count_subq.label("message_count"),
    )

    scope_clauses = []
    if user_id is not None:
        scope_clauses.append(Session.user_id == user_id)
    if include_escalated:
        scope_clauses.append(Session.status == SessionStatus.ESCALATED)
    if not scope_clauses:
        return [], None
    stmt = stmt.where(or_(*scope_clauses)) if len(scope_clauses) > 1 else stmt.where(scope_clauses[0])

    if cursor is not None:
        cursor_updated_at, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Session.updated_at < cursor_updated_at,
                and_(
                    Session.updated_at == cursor_updated_at,
                    Session.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(Session.updated_at.desc(), Session.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    rows = list(result.all())

    has_more = len(rows) > limit
    page = rows[:limit]

    items = [
        {
            "id": row.id,
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "last_message_preview": _extract_preview(row.last_content),
            "message_count": row.message_count or 0,
        }
        for row in page
    ]

    next_cursor = (
        _encode_cursor(page[-1].updated_at, page[-1].id) if has_more and page else None
    )

    return items, next_cursor


# ============================================================================
# Participants
# ============================================================================


async def get_participant_by_ndis_number(
    db: AsyncSession, ndis_number: str
) -> Participant | None:
    stmt = select(Participant).where(
        Participant.ndis_number == ndis_number,
        Participant.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_participant(db: AsyncSession, participant_id: str) -> Participant | None:
    stmt = select(Participant).where(
        Participant.id == participant_id,
        Participant.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def search_participants_by_name(
    db: AsyncSession, query: str, limit: int = 5
) -> list[Participant]:
    pattern = f"%{query.lower()}%"
    stmt = (
        select(Participant)
        .where(Participant.deleted_at.is_(None))
        .where(
            or_(
                func.lower(Participant.first_name).like(pattern),
                func.lower(Participant.last_name).like(pattern),
                func.lower(Participant.preferred_name).like(pattern),
                func.lower(Participant.email).like(pattern),
            )
        )
        .order_by(Participant.last_name, Participant.first_name)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_participant(db: AsyncSession, **fields) -> Participant:
    """Insert a new participant row and return it with the generated ID."""
    p = Participant(**fields)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def update_participant(
    db: AsyncSession, participant_id: str, **fields
) -> Participant | None:
    """Apply a partial update to a live participant. Returns the row, or None if missing."""
    stmt = select(Participant).where(
        Participant.id == participant_id,
        Participant.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    p = result.scalar_one_or_none()
    if p is None:
        return None
    for key, value in fields.items():
        setattr(p, key, value)
    await db.commit()
    await db.refresh(p)
    return p


async def get_contacts_for_participant(
    db: AsyncSession, participant_id: str
) -> list[Contact]:
    stmt = (
        select(Contact)
        .where(
            Contact.participant_id == participant_id,
            Contact.deleted_at.is_(None),
        )
        .order_by(Contact.is_primary.desc(), Contact.is_emergency.desc(), Contact.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Service catalog
# ============================================================================


async def list_active_service_types(db: AsyncSession) -> list[ServiceType]:
    stmt = (
        select(ServiceType)
        .where(ServiceType.status == ServiceTypeStatus.ACTIVE)
        .order_by(ServiceType.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Plans, goals, service agreements
# ============================================================================


async def get_active_plan_for_participant(
    db: AsyncSession, participant_id: str
) -> Plan | None:
    stmt = (
        select(Plan)
        .where(
            Plan.participant_id == participant_id,
            Plan.status == PlanStatus.ACTIVE,
            Plan.deleted_at.is_(None),
        )
        .order_by(Plan.start_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_goals_for_participant(
    db: AsyncSession,
    participant_id: str,
    include_inactive: bool = False,
) -> list[Goal]:
    stmt = select(Goal).where(Goal.participant_id == participant_id)
    if not include_inactive:
        stmt = stmt.where(Goal.status == GoalStatus.ACTIVE)
    stmt = stmt.order_by(Goal.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active_service_agreements_for_participant(
    db: AsyncSession, participant_id: str
) -> list[tuple[ServiceAgreement, ServiceType]]:
    stmt = (
        select(ServiceAgreement, ServiceType)
        .join(ServiceType, ServiceType.id == ServiceAgreement.service_type_id)
        .where(
            ServiceAgreement.participant_id == participant_id,
            ServiceAgreement.status == AgreementStatus.ACTIVE,
            ServiceAgreement.deleted_at.is_(None),
        )
        .order_by(ServiceType.name)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


# ============================================================================
# Knowledge base
# ============================================================================


async def list_participants(
    db: AsyncSession,
    search: str | None = None,
    status: ParticipantStatus | None = None,
    limit: int = 50,
) -> list[dict]:
    """List participants with primary contact + active plan inlined (no N+1)."""

    primary_contact_subq = (
        select(Contact.name)
        .where(
            Contact.participant_id == Participant.id,
            Contact.is_primary.is_(True),
            Contact.deleted_at.is_(None),
        )
        .order_by(Contact.created_at)
        .limit(1)
        .correlate(Participant)
        .scalar_subquery()
    )
    primary_contact_rel_subq = (
        select(Contact.relationship_type)
        .where(
            Contact.participant_id == Participant.id,
            Contact.is_primary.is_(True),
            Contact.deleted_at.is_(None),
        )
        .order_by(Contact.created_at)
        .limit(1)
        .correlate(Participant)
        .scalar_subquery()
    )
    plan_mgmt_subq = (
        select(Plan.management_type)
        .where(
            Plan.participant_id == Participant.id,
            Plan.status == PlanStatus.ACTIVE,
            Plan.deleted_at.is_(None),
        )
        .order_by(Plan.start_date.desc())
        .limit(1)
        .correlate(Participant)
        .scalar_subquery()
    )

    stmt = select(
        Participant.id,
        Participant.ndis_number,
        Participant.first_name,
        Participant.last_name,
        Participant.preferred_name,
        Participant.primary_disability_category,
        Participant.suburb,
        Participant.state,
        Participant.status,
        primary_contact_subq.label("primary_contact_name"),
        primary_contact_rel_subq.label("primary_contact_relationship"),
        plan_mgmt_subq.label("active_plan_management_type"),
    ).where(Participant.deleted_at.is_(None))

    if status is not None:
        stmt = stmt.where(Participant.status == status)

    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Participant.first_name).like(pattern),
                func.lower(Participant.last_name).like(pattern),
                func.lower(Participant.preferred_name).like(pattern),
                Participant.ndis_number.like(f"%{search}%"),
                func.lower(Participant.suburb).like(pattern),
            )
        )

    stmt = stmt.order_by(Participant.last_name, Participant.first_name).limit(limit)
    result = await db.execute(stmt)

    items = []
    for row in result.all():
        items.append({
            "id": row.id,
            "ndis_number": row.ndis_number,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "preferred_name": row.preferred_name,
            "primary_disability_category": (
                row.primary_disability_category.value
                if row.primary_disability_category is not None else None
            ),
            "suburb": row.suburb,
            "state": row.state.value if row.state is not None else None,
            "status": row.status.value,
            "primary_contact_name": row.primary_contact_name,
            "primary_contact_relationship": (
                row.primary_contact_relationship.value
                if row.primary_contact_relationship is not None else None
            ),
            "active_plan_management_type": (
                row.active_plan_management_type.value
                if row.active_plan_management_type is not None else None
            ),
        })
    return items


async def count_participants(
    db: AsyncSession, status: ParticipantStatus | None = None
) -> int:
    stmt = (
        select(func.count(Participant.id))
        .where(Participant.deleted_at.is_(None))
    )
    if status is not None:
        stmt = stmt.where(Participant.status == status)
    return (await db.execute(stmt)).scalar_one()


async def get_assigned_staff_for_participant(
    db: AsyncSession, participant_id: str
) -> list[tuple[ParticipantStaffAssignment, Staff]]:
    stmt = (
        select(ParticipantStaffAssignment, Staff)
        .join(Staff, Staff.id == ParticipantStaffAssignment.staff_id)
        .where(
            ParticipantStaffAssignment.participant_id == participant_id,
            ParticipantStaffAssignment.valid_to.is_(None),
        )
        .order_by(ParticipantStaffAssignment.assignment_type, Staff.last_name)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def list_staff(db: AsyncSession) -> list[Staff]:
    stmt = (
        select(Staff)
        .where(Staff.deleted_at.is_(None))
        .order_by(Staff.last_name, Staff.first_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_knowledge_articles(
    db: AsyncSession, status: KnowledgeStatus | None = None
) -> list[KnowledgeArticle]:
    stmt = select(KnowledgeArticle).order_by(KnowledgeArticle.updated_at.desc())
    if status is not None:
        stmt = stmt.where(KnowledgeArticle.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def dashboard_counts(db: AsyncSession) -> dict:
    """Aggregate counts for the dashboard."""

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    async def count(stmt):
        return (await db.execute(stmt)).scalar_one() or 0

    return {
        "active_participants": await count(
            select(func.count(Participant.id)).where(
                Participant.status == ParticipantStatus.ACTIVE,
                Participant.deleted_at.is_(None),
            )
        ),
        "onboarding_participants": await count(
            select(func.count(Participant.id)).where(
                Participant.status == ParticipantStatus.ONBOARDING,
                Participant.deleted_at.is_(None),
            )
        ),
        "active_plans": await count(
            select(func.count(Plan.id)).where(
                Plan.status == PlanStatus.ACTIVE, Plan.deleted_at.is_(None)
            )
        ),
        "draft_plans": await count(
            select(func.count(Plan.id)).where(
                Plan.status == PlanStatus.DRAFT, Plan.deleted_at.is_(None)
            )
        ),
        "active_agreements": await count(
            select(func.count(ServiceAgreement.id)).where(
                ServiceAgreement.status == AgreementStatus.ACTIVE,
                ServiceAgreement.deleted_at.is_(None),
            )
        ),
        "draft_agreements": await count(
            select(func.count(ServiceAgreement.id)).where(
                ServiceAgreement.status == AgreementStatus.DRAFT,
                ServiceAgreement.deleted_at.is_(None),
            )
        ),
        "conversations_today": await count(
            select(func.count(Session.id)).where(
                Session.created_at >= today_start
            )
        ),
        "escalated_today": await count(
            select(func.count(Session.id)).where(
                Session.status == SessionStatus.ESCALATED,
                Session.created_at >= today_start,
            )
        ),
    }


async def search_knowledge_articles(
    db: AsyncSession, query: str, limit: int = 5
) -> list[KnowledgeArticle]:
    keywords = [k for k in query.lower().split() if k]
    if not keywords:
        return []

    conditions = []
    for kw in keywords:
        pattern = f"%{kw}%"
        conditions.append(func.lower(KnowledgeArticle.title).like(pattern))
        conditions.append(func.lower(KnowledgeArticle.body_md).like(pattern))

    stmt = (
        select(KnowledgeArticle)
        .where(KnowledgeArticle.status == KnowledgeStatus.PUBLISHED)
        .where(or_(*conditions))
        .order_by(KnowledgeArticle.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Shifts (Phase 3)
# ============================================================================


async def get_upcoming_shifts(
    db: AsyncSession,
    participant_id: str,
    limit: int = 5,
) -> list[tuple[Shift, ServiceType, Staff | None]]:
    """Next N scheduled shifts for a participant, soonest first."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Shift, ServiceType, Staff)
        .join(ServiceType, ServiceType.id == Shift.service_type_id)
        .join(Staff, Staff.id == Shift.staff_id, isouter=True)
        .where(
            Shift.participant_id == participant_id,
            Shift.scheduled_start >= now,
            Shift.status == ShiftStatus.SCHEDULED,
        )
        .order_by(Shift.scheduled_start.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]


async def get_recent_shifts(
    db: AsyncSession,
    participant_id: str,
    limit: int = 5,
) -> list[tuple[Shift, ServiceType, Staff | None]]:
    """Most recent completed (or attempted) shifts for a participant."""
    stmt = (
        select(Shift, ServiceType, Staff)
        .join(ServiceType, ServiceType.id == Shift.service_type_id)
        .join(Staff, Staff.id == Shift.staff_id, isouter=True)
        .where(
            Shift.participant_id == participant_id,
            Shift.status.in_(
                [
                    ShiftStatus.COMPLETED,
                    ShiftStatus.CANCELLED_BY_PARTICIPANT,
                    ShiftStatus.CANCELLED_BY_PROVIDER,
                    ShiftStatus.NO_SHOW,
                ]
            ),
        )
        .order_by(Shift.scheduled_start.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]


# ============================================================================
# Medications (Phase 4)
# ============================================================================


async def get_active_medications(
    db: AsyncSession, participant_id: str
) -> list[MedicationRecord]:
    stmt = (
        select(MedicationRecord)
        .where(
            MedicationRecord.participant_id == participant_id,
            MedicationRecord.status == MedicationStatus.ACTIVE,
            MedicationRecord.deleted_at.is_(None),
        )
        .order_by(MedicationRecord.medication_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_recent_med_admin(
    db: AsyncSession, participant_id: str, limit: int = 10
) -> list[MedicationAdministrationLog]:
    stmt = (
        select(MedicationAdministrationLog)
        .where(MedicationAdministrationLog.participant_id == participant_id)
        .order_by(MedicationAdministrationLog.administered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Preferences (Phase 4)
# ============================================================================


async def get_preferences(
    db: AsyncSession,
    participant_id: str,
    category: PreferenceCategory | None = None,
) -> list[ParticipantPreference]:
    stmt = select(ParticipantPreference).where(
        ParticipantPreference.participant_id == participant_id
    )
    if category is not None:
        stmt = stmt.where(ParticipantPreference.category == category)
    stmt = stmt.order_by(
        ParticipantPreference.priority, ParticipantPreference.created_at.desc()
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Incidents (Phase 4)
# ============================================================================


async def get_open_incidents_for_participant(
    db: AsyncSession, participant_id: str
) -> list[Incident]:
    stmt = (
        select(Incident)
        .where(
            Incident.participant_id == participant_id,
            Incident.status.in_(
                [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]
            ),
        )
        .order_by(Incident.occurred_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Risk + restrictive practices (Phase 4)
# ============================================================================


async def get_current_risk_assessments(
    db: AsyncSession, participant_id: str
) -> list[RiskAssessment]:
    """Risk assessments not superseded by a newer version."""
    stmt = (
        select(RiskAssessment)
        .where(
            RiskAssessment.participant_id == participant_id,
            RiskAssessment.superseded_by_id.is_(None),
        )
        .order_by(RiskAssessment.assessed_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active_restrictive_practices(
    db: AsyncSession, participant_id: str
) -> list[RestrictivePractice]:
    stmt = (
        select(RestrictivePractice)
        .where(
            RestrictivePractice.participant_id == participant_id,
            RestrictivePractice.status == RestrictivePracticeStatus.ACTIVE,
        )
        .order_by(RestrictivePractice.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Progress notes (Phase 4)
# ============================================================================


async def get_recent_progress_notes(
    db: AsyncSession, participant_id: str, limit: int = 10
) -> list[ProgressNote]:
    stmt = (
        select(ProgressNote)
        .where(ProgressNote.participant_id == participant_id)
        .order_by(ProgressNote.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# Audit log (Phase 4) — surfaces "what changed" for a participant
# ============================================================================


_PARTICIPANT_LINKED_TABLES = (
    "participants",
    "contacts",
    "participant_staff_assignments",
    "plans",
    "goals",
    "service_agreements",
    "shifts",
    "progress_notes",
    "incidents",
    "incident_followups",
    "medication_records",
    "medication_administration_log",
    "restrictive_practices",
    "risk_assessments",
    "documents",
)


async def get_participant_audit_history(
    db: AsyncSession, participant_id: str, limit: int = 20
) -> list[AuditLog]:
    """Return recent audit-log entries that touch a participant.

    Matches when the participant's id appears either as the audited record
    (table=participants) or in a participant_id field on a child row.
    Uses Postgres ``->>`` JSON access; SQLite callers should not hit this.
    """
    pid = participant_id
    new_pid = AuditLog.new_values.op("->>")("participant_id")
    old_pid = AuditLog.old_values.op("->>")("participant_id")
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.table_name.in_(_PARTICIPANT_LINKED_TABLES),
            or_(
                and_(AuditLog.table_name == "participants", AuditLog.record_id == pid),
                new_pid == pid,
                old_pid == pid,
            ),
        )
        .order_by(AuditLog.changed_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
