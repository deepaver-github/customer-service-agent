from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Existing session ID to continue a conversation")
    message: str = Field(description="The user's message")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    escalated: bool = False
    tools_used: list[str] = Field(default_factory=list)


class SessionCreate(BaseModel):
    metadata: dict | None = Field(default=None, description="Optional session metadata")
    participant_id: str | None = Field(
        default=None,
        description="Optional Special Care Australia participant id this session is on behalf of",
    )
    staff_id: str | None = Field(
        default=None,
        description="Optional staff id if a staff member is using the assistant",
    )


class SessionResponse(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: dict | None = None
    participant_id: str | None = None
    staff_id: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | dict | list
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class SessionListItem(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    items: list[SessionListItem] = Field(default_factory=list)
    next_cursor: str | None = None


class ErrorResponse(BaseModel):
    error: str
    code: str


# ============================================================================
# Participant API models
# ============================================================================


class ContactItem(BaseModel):
    id: str
    name: str
    relationship: str
    phone: str | None = None
    email: str | None = None
    is_primary: bool = False
    is_emergency: bool = False
    notes: str | None = None

    model_config = {"from_attributes": True}


class GoalItem(BaseModel):
    id: str
    description: str
    category: str
    target_date: date | None = None
    status: str

    model_config = {"from_attributes": True}


class ActivePlanItem(BaseModel):
    id: str
    plan_number: str
    start_date: date
    end_date: date
    management_type: str
    plan_manager_name: str | None = None
    plan_manager_contact: str | None = None
    status: str

    model_config = {"from_attributes": True}


class ServiceAgreementItem(BaseModel):
    id: str
    service_code: str
    service_name: str
    valid_from: date
    valid_to: date | None = None
    scope_notes: str | None = None
    status: str


class StaffAssignmentItem(BaseModel):
    staff_id: str
    staff_name: str
    staff_role: str
    assignment_type: str
    valid_from: date


class ParticipantCreateRequest(BaseModel):
    """Payload for POST /participants — required + most-used optional fields."""

    ndis_number: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    dob: date | None = None
    primary_disability_category: str | None = None
    communication_needs: str | None = None
    address_line1: str | None = Field(default=None, max_length=255)
    suburb: str | None = Field(default=None, max_length=100)
    state: str | None = None
    postcode: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    status: str = Field(default="onboarding")


class ParticipantUpdateRequest(BaseModel):
    """Payload for PATCH /participants/{id}. All fields optional; only provided keys are applied."""

    ndis_number: str | None = Field(default=None, min_length=1, max_length=20)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    dob: date | None = None
    primary_disability_category: str | None = None
    communication_needs: str | None = None
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    suburb: str | None = Field(default=None, max_length=100)
    state: str | None = None
    postcode: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    status: str | None = None


class ParticipantListItem(BaseModel):
    id: str
    ndis_number: str
    first_name: str
    last_name: str
    preferred_name: str | None = None
    primary_disability_category: str | None = None
    suburb: str | None = None
    state: str | None = None
    status: str
    primary_contact_name: str | None = None
    primary_contact_relationship: str | None = None
    active_plan_management_type: str | None = None


class ParticipantListResponse(BaseModel):
    items: list[ParticipantListItem] = Field(default_factory=list)
    total: int = 0


class ShiftItem(BaseModel):
    id: str
    service_name: str
    service_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    location: str | None = None
    support_worker_name: str | None = None
    status: str
    cancelled_reason: str | None = None


class MedicationItem(BaseModel):
    id: str
    medication_name: str
    dose: str
    route: str
    frequency: str
    prn: bool = False
    prescriber: str | None = None
    start_date: date
    end_date: date | None = None
    notes: str | None = None
    status: str


class PreferenceItem(BaseModel):
    id: str
    category: str
    priority: str
    detail: str


class IncidentItem(BaseModel):
    id: str
    incident_type: str
    category: str
    status: str
    occurred_at: datetime
    location: str | None = None
    summary: str


class RiskAssessmentItem(BaseModel):
    id: str
    assessment_type: str
    level: str
    controls: str
    assessed_at: datetime
    review_due: date | None = None


class RestrictivePracticeItem(BaseModel):
    id: str
    practice_type: str
    status: str
    authorisation_ref: str | None = None
    authorised_from: date | None = None
    authorised_to: date | None = None
    notes: str | None = None


class AuditChangeItem(BaseModel):
    table: str
    record_id: str
    action: str
    changed_at: datetime


class ParticipantDetailResponse(BaseModel):
    id: str
    ndis_number: str
    first_name: str
    last_name: str
    preferred_name: str | None = None
    dob: date | None = None
    primary_disability_category: str | None = None
    communication_needs: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    created_at: datetime
    contacts: list[ContactItem] = Field(default_factory=list)
    active_plan: ActivePlanItem | None = None
    goals: list[GoalItem] = Field(default_factory=list)
    service_agreements: list[ServiceAgreementItem] = Field(default_factory=list)
    assigned_staff: list[StaffAssignmentItem] = Field(default_factory=list)
    upcoming_shifts: list[ShiftItem] = Field(default_factory=list)
    recent_shifts: list[ShiftItem] = Field(default_factory=list)
    medications: list[MedicationItem] = Field(default_factory=list)
    preferences: list[PreferenceItem] = Field(default_factory=list)
    open_incidents: list[IncidentItem] = Field(default_factory=list)
    risk_assessments: list[RiskAssessmentItem] = Field(default_factory=list)
    restrictive_practices: list[RestrictivePracticeItem] = Field(default_factory=list)
    recent_changes: list[AuditChangeItem] = Field(default_factory=list)


class StaffListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    role: str
    status: str
    email: str | None = None

    model_config = {"from_attributes": True}


class KnowledgeListItem(BaseModel):
    id: str
    title: str
    category: str
    status: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: str
    password: str


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    role: str
    staff_id: str | None = None
    participant_id: str | None = None
    name: str | None = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    user: CurrentUserResponse


class DashboardStats(BaseModel):
    active_participants: int
    onboarding_participants: int
    active_plans: int
    draft_plans: int
    active_agreements: int
    draft_agreements: int
    conversations_today: int
    escalated_today: int
