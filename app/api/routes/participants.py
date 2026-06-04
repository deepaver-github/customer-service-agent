from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError

from app.api.models import (
    ActivePlanItem,
    AuditChangeItem,
    ContactItem,
    GoalItem,
    IncidentItem,
    MedicationItem,
    ParticipantCreateRequest,
    ParticipantDetailResponse,
    ParticipantListItem,
    ParticipantListResponse,
    ParticipantUpdateRequest,
    PreferenceItem,
    RestrictivePracticeItem,
    RiskAssessmentItem,
    ServiceAgreementItem,
    ShiftItem,
    StaffAssignmentItem,
)
from app.auth.dependencies import current_staff, current_user, participant_can_access
from app.memory import repository as repo
from app.memory.database import get_db
from app.memory.models import (
    AustralianState,
    DisabilityCategory,
    ParticipantStatus,
    User,
)

router = APIRouter()


@router.get("", response_model=ParticipantListResponse)
async def list_participants(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_staff),
):
    status_filter: ParticipantStatus | None = None
    if status:
        try:
            status_filter = ParticipantStatus(status.lower())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from exc

    rows = await repo.list_participants(
        db, search=search, status=status_filter, limit=limit
    )
    total = await repo.count_participants(db, status=status_filter)

    return ParticipantListResponse(
        items=[ParticipantListItem(**row) for row in rows],
        total=total,
    )


def _parse_enum(enum_cls, value: str | None, field: str):
    if value is None or value == "":
        return None
    try:
        return enum_cls(value)
    except ValueError as exc:
        valid = ", ".join(m.value for m in enum_cls)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field}: {value!r}. Allowed: {valid}.",
        ) from exc


@router.post("", response_model=ParticipantDetailResponse, status_code=201)
async def create_participant(
    payload: ParticipantCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_staff),
):
    fields = {
        "ndis_number": payload.ndis_number.strip(),
        "first_name": payload.first_name.strip(),
        "last_name": payload.last_name.strip(),
        "preferred_name": (payload.preferred_name or None) and payload.preferred_name.strip(),
        "dob": payload.dob,
        "communication_needs": payload.communication_needs,
        "address_line1": payload.address_line1,
        "suburb": payload.suburb,
        "postcode": payload.postcode,
        "phone": payload.phone,
        "email": payload.email,
        "primary_disability_category": _parse_enum(
            DisabilityCategory,
            payload.primary_disability_category,
            "primary_disability_category",
        ),
        "state": _parse_enum(AustralianState, payload.state, "state"),
        "status": _parse_enum(ParticipantStatus, payload.status, "status")
                  or ParticipantStatus.ONBOARDING,
    }
    try:
        created = await repo.create_participant(db, **fields)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"NDIS number {payload.ndis_number!r} is already in use.",
        ) from exc

    # Re-use the detail endpoint shape by calling our own get function.
    return await get_participant(created.id, db=db, user=_)


_ENUM_FIELDS = {
    "primary_disability_category": DisabilityCategory,
    "state": AustralianState,
    "status": ParticipantStatus,
}

_STRINGISH_FIELDS = {
    "ndis_number",
    "first_name",
    "last_name",
    "preferred_name",
    "communication_needs",
    "address_line1",
    "address_line2",
    "suburb",
    "postcode",
    "phone",
    "email",
}


@router.patch("/{participant_id}", response_model=ParticipantDetailResponse)
async def update_participant(
    participant_id: str,
    payload: ParticipantUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_staff),
):
    """Apply a partial update to a participant. Only fields present in the payload are changed."""
    provided = payload.model_dump(exclude_unset=True)
    if not provided:
        raise HTTPException(status_code=400, detail="No fields supplied to update.")

    fields: dict = {}
    for key, value in provided.items():
        if key in _ENUM_FIELDS:
            parsed = _parse_enum(_ENUM_FIELDS[key], value, key)
            if parsed is None and key == "status":
                # status is non-nullable on the model — reject explicit null
                raise HTTPException(status_code=400, detail="status cannot be empty.")
            fields[key] = parsed
        elif key in _STRINGISH_FIELDS and isinstance(value, str):
            stripped = value.strip()
            fields[key] = stripped or None
        else:
            fields[key] = value

    # ndis_number is required on the model — don't allow blanking it out.
    if "ndis_number" in fields and not fields["ndis_number"]:
        raise HTTPException(status_code=400, detail="NDIS number cannot be empty.")
    if "first_name" in fields and not fields["first_name"]:
        raise HTTPException(status_code=400, detail="First name cannot be empty.")
    if "last_name" in fields and not fields["last_name"]:
        raise HTTPException(status_code=400, detail="Last name cannot be empty.")

    try:
        updated = await repo.update_participant(db, participant_id, **fields)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"NDIS number {fields.get('ndis_number')!r} is already in use.",
        ) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Participant not found")

    return await get_participant(participant_id, db=db, user=user)


@router.get("/{participant_id}", response_model=ParticipantDetailResponse)
async def get_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    if not participant_can_access(user, participant_id):
        raise HTTPException(status_code=403, detail="You can only view your own record.")

    p = await repo.get_participant(db, participant_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Participant not found")

    contacts = await repo.get_contacts_for_participant(db, participant_id)
    goals = await repo.get_goals_for_participant(db, participant_id, include_inactive=True)
    plan = await repo.get_active_plan_for_participant(db, participant_id)
    agreements_rows = await repo.get_active_service_agreements_for_participant(
        db, participant_id
    )
    assigned = await repo.get_assigned_staff_for_participant(db, participant_id)
    upcoming_rows = await repo.get_upcoming_shifts(db, participant_id, limit=10)
    recent_rows = await repo.get_recent_shifts(db, participant_id, limit=10)
    medications = await repo.get_active_medications(db, participant_id)
    preferences = await repo.get_preferences(db, participant_id)
    open_incidents = await repo.get_open_incidents_for_participant(db, participant_id)
    risk_assessments = await repo.get_current_risk_assessments(db, participant_id)
    restrictive_practices = await repo.get_active_restrictive_practices(db, participant_id)
    # Audit history is Postgres-only (JSON cast). Swallow on SQLite/dev fallback.
    try:
        recent_changes = await repo.get_participant_audit_history(
            db, participant_id, limit=20
        )
    except Exception:
        recent_changes = []

    active_plan = None
    if plan is not None:
        active_plan = ActivePlanItem(
            id=plan.id,
            plan_number=plan.plan_number,
            start_date=plan.start_date,
            end_date=plan.end_date,
            management_type=plan.management_type.value,
            plan_manager_name=plan.plan_manager_name,
            plan_manager_contact=plan.plan_manager_contact,
            status=plan.status.value,
        )

    return ParticipantDetailResponse(
        id=p.id,
        ndis_number=p.ndis_number,
        first_name=p.first_name,
        last_name=p.last_name,
        preferred_name=p.preferred_name,
        dob=p.dob,
        primary_disability_category=(
            p.primary_disability_category.value
            if p.primary_disability_category is not None else None
        ),
        communication_needs=p.communication_needs,
        address_line1=p.address_line1,
        address_line2=p.address_line2,
        suburb=p.suburb,
        state=p.state.value if p.state is not None else None,
        postcode=p.postcode,
        phone=p.phone,
        email=p.email,
        status=p.status.value,
        created_at=p.created_at,
        contacts=[
            ContactItem(
                id=c.id,
                name=c.name,
                relationship=c.relationship_type.value,
                phone=c.phone,
                email=c.email,
                is_primary=c.is_primary,
                is_emergency=c.is_emergency,
                notes=c.notes,
            )
            for c in contacts
        ],
        active_plan=active_plan,
        goals=[
            GoalItem(
                id=g.id,
                description=g.description,
                category=g.category.value,
                target_date=g.target_date,
                status=g.status.value,
            )
            for g in goals
        ],
        service_agreements=[
            ServiceAgreementItem(
                id=agreement.id,
                service_code=st.code,
                service_name=st.name,
                valid_from=agreement.valid_from,
                valid_to=agreement.valid_to,
                scope_notes=agreement.scope_notes,
                status=agreement.status.value,
            )
            for agreement, st in agreements_rows
        ],
        assigned_staff=[
            StaffAssignmentItem(
                staff_id=staff.id,
                staff_name=f"{staff.first_name} {staff.last_name}",
                staff_role=staff.role.value,
                assignment_type=assignment.assignment_type.value,
                valid_from=assignment.valid_from,
            )
            for assignment, staff in assigned
        ],
        upcoming_shifts=[
            ShiftItem(
                id=shift.id,
                service_name=st.name,
                service_code=st.code,
                scheduled_start=shift.scheduled_start,
                scheduled_end=shift.scheduled_end,
                actual_start=shift.actual_start,
                actual_end=shift.actual_end,
                location=shift.location,
                support_worker_name=(
                    f"{staff_row.first_name} {staff_row.last_name}"
                    if staff_row is not None else None
                ),
                status=shift.status.value,
                cancelled_reason=shift.cancelled_reason,
            )
            for shift, st, staff_row in upcoming_rows
        ],
        recent_shifts=[
            ShiftItem(
                id=shift.id,
                service_name=st.name,
                service_code=st.code,
                scheduled_start=shift.scheduled_start,
                scheduled_end=shift.scheduled_end,
                actual_start=shift.actual_start,
                actual_end=shift.actual_end,
                location=shift.location,
                support_worker_name=(
                    f"{staff_row.first_name} {staff_row.last_name}"
                    if staff_row is not None else None
                ),
                status=shift.status.value,
                cancelled_reason=shift.cancelled_reason,
            )
            for shift, st, staff_row in recent_rows
        ],
        medications=[
            MedicationItem(
                id=m.id,
                medication_name=m.medication_name,
                dose=m.dose,
                route=m.route.value,
                frequency=m.frequency,
                prn=m.prn,
                prescriber=m.prescriber,
                start_date=m.start_date,
                end_date=m.end_date,
                notes=m.notes,
                status=m.status.value,
            )
            for m in medications
        ],
        preferences=[
            PreferenceItem(
                id=pref.id,
                category=pref.category.value,
                priority=pref.priority.value,
                detail=pref.detail,
            )
            for pref in preferences
        ],
        open_incidents=[
            IncidentItem(
                id=inc.id,
                incident_type=inc.incident_type.value,
                category=inc.category.value,
                status=inc.status.value,
                occurred_at=inc.occurred_at,
                location=inc.location,
                summary=inc.summary,
            )
            for inc in open_incidents
        ],
        risk_assessments=[
            RiskAssessmentItem(
                id=r.id,
                assessment_type=r.assessment_type.value,
                level=r.level.value,
                controls=r.controls,
                assessed_at=r.assessed_at,
                review_due=r.review_due,
            )
            for r in risk_assessments
        ],
        restrictive_practices=[
            RestrictivePracticeItem(
                id=rp.id,
                practice_type=rp.practice_type.value,
                status=rp.status.value,
                authorisation_ref=rp.authorisation_ref,
                authorised_from=rp.authorised_from,
                authorised_to=rp.authorised_to,
                notes=rp.notes,
            )
            for rp in restrictive_practices
        ],
        recent_changes=[
            AuditChangeItem(
                table=entry.table_name,
                record_id=entry.record_id,
                action=(
                    entry.action.value if hasattr(entry.action, "value")
                    else str(entry.action)
                ),
                changed_at=entry.changed_at,
            )
            for entry in recent_changes
        ],
    )
