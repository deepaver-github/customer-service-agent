from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ============================================================================
# Chat session + messages (existing, with new participant/staff linkage)
# ============================================================================


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=None
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE
    )
    participant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    staff_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="session", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[dict | list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped[Session] = relationship(back_populates="messages")


# ============================================================================
# Audit log (existing — append-only, populated by Postgres triggers)
# ============================================================================


class AuditAction(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    table_name: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction))
    old_values: Mapped[dict | None] = mapped_column(JSON, default=None)
    new_values: Mapped[dict | None] = mapped_column(JSON, default=None)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Participants
# ============================================================================


class DisabilityCategory(str, enum.Enum):
    INTELLECTUAL = "intellectual"
    AUTISM = "autism"
    PSYCHOSOCIAL = "psychosocial"
    PHYSICAL = "physical"
    SENSORY = "sensory"
    NEUROLOGICAL = "neurological"
    ACQUIRED_BRAIN_INJURY = "acquired_brain_injury"
    OTHER = "other"


class ParticipantStatus(str, enum.Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    EXITED = "exited"


class AustralianState(str, enum.Enum):
    ACT = "ACT"
    NSW = "NSW"
    NT = "NT"
    QLD = "QLD"
    SA = "SA"
    TAS = "TAS"
    VIC = "VIC"
    WA = "WA"


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ndis_number: Mapped[str] = mapped_column(String(20))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    preferred_name: Mapped[str | None] = mapped_column(String(100), default=None)
    dob: Mapped[date | None] = mapped_column(Date, default=None)
    primary_disability_category: Mapped[DisabilityCategory | None] = mapped_column(
        Enum(DisabilityCategory), default=None
    )
    communication_needs: Mapped[str | None] = mapped_column(Text, default=None)
    address_line1: Mapped[str | None] = mapped_column(String(255), default=None)
    address_line2: Mapped[str | None] = mapped_column(String(255), default=None)
    suburb: Mapped[str | None] = mapped_column(String(100), default=None)
    state: Mapped[AustralianState | None] = mapped_column(
        Enum(AustralianState), default=None
    )
    postcode: Mapped[str | None] = mapped_column(String(10), default=None)
    phone: Mapped[str | None] = mapped_column(String(30), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(ParticipantStatus), default=ParticipantStatus.ONBOARDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    contacts: Mapped[list[Contact]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_participants_ndis_number_live",
            "ndis_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# ============================================================================
# Contacts
# ============================================================================


class ContactRelationship(str, enum.Enum):
    FAMILY = "family"
    GUARDIAN = "guardian"
    SUPPORT_COORDINATOR = "support_coordinator"
    PLAN_MANAGER = "plan_manager"
    GP = "gp"
    ADVOCATE = "advocate"
    EMERGENCY = "emergency"
    OTHER = "other"


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    relationship_type: Mapped[ContactRelationship] = mapped_column(
        "relationship", Enum(ContactRelationship)
    )
    phone: Mapped[str | None] = mapped_column(String(30), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    participant: Mapped[Participant] = relationship(back_populates="contacts")


# ============================================================================
# Staff
# ============================================================================


class StaffRole(str, enum.Enum):
    SUPPORT_WORKER = "support_worker"
    COORDINATOR = "coordinator"
    MANAGER = "manager"
    CLINICAL_LEAD = "clinical_lead"


class StaffStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    INACTIVE = "inactive"


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    phone: Mapped[str | None] = mapped_column(String(30), default=None)
    role: Mapped[StaffRole] = mapped_column(
        Enum(StaffRole), default=StaffRole.SUPPORT_WORKER
    )
    ndis_worker_check_expiry: Mapped[date | None] = mapped_column(Date, default=None)
    wwcc_expiry: Mapped[date | None] = mapped_column(Date, default=None)
    police_check_expiry: Mapped[date | None] = mapped_column(Date, default=None)
    qualifications: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[StaffStatus] = mapped_column(
        Enum(StaffStatus), default=StaffStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


# ============================================================================
# Participant ↔ Staff assignments
# ============================================================================


class AssignmentType(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DO_NOT_ROSTER = "do_not_roster"


class ParticipantStaffAssignment(Base):
    __tablename__ = "participant_staff_assignments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    assignment_type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType), default=AssignmentType.PRIMARY
    )
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Service catalog (no rates — billing excluded)
# ============================================================================


class NDISCategory(str, enum.Enum):
    CORE = "core"
    CAPACITY_BUILDING = "capacity_building"
    CAPITAL = "capital"


class ServiceTypeStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ServiceType(Base):
    __tablename__ = "service_types"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    ndis_category: Mapped[NDISCategory] = mapped_column(
        Enum(NDISCategory), default=NDISCategory.CORE
    )
    status: Mapped[ServiceTypeStatus] = mapped_column(
        Enum(ServiceTypeStatus), default=ServiceTypeStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Knowledge base (replaces faq_entries)
# ============================================================================


class KnowledgeCategory(str, enum.Enum):
    ABOUT_SERVICES = "about_services"
    NDIS_BASICS = "ndis_basics"
    GETTING_STARTED = "getting_started"
    SUPPORTS_EXPLAINED = "supports_explained"
    COMPLAINTS_FEEDBACK = "complaints_feedback"
    OTHER = "other"


class KnowledgeStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    body_md: Mapped[str] = mapped_column(Text)
    category: Mapped[KnowledgeCategory] = mapped_column(
        Enum(KnowledgeCategory), default=KnowledgeCategory.OTHER
    )
    tags: Mapped[list | None] = mapped_column(JSON, default=None)
    status: Mapped[KnowledgeStatus] = mapped_column(
        Enum(KnowledgeStatus), default=KnowledgeStatus.PUBLISHED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ============================================================================
# NDIS plans (Phase 2)
# ============================================================================


class PlanManagementType(str, enum.Enum):
    SELF = "self"
    PLAN_MANAGED = "plan_managed"
    AGENCY_MANAGED = "agency_managed"


class PlanStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    plan_number: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    management_type: Mapped[PlanManagementType] = mapped_column(
        Enum(PlanManagementType), default=PlanManagementType.PLAN_MANAGED
    )
    plan_manager_name: Mapped[str | None] = mapped_column(String(200), default=None)
    plan_manager_contact: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus), default=PlanStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    __table_args__ = (
        Index(
            "ix_plans_plan_number_live",
            "plan_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


# ============================================================================
# Goals (Phase 2)
# ============================================================================


class GoalCategory(str, enum.Enum):
    INDEPENDENCE = "independence"
    COMMUNITY = "community"
    EMPLOYMENT = "employment"
    HEALTH = "health"
    RELATIONSHIPS = "relationships"
    LEARNING = "learning"
    OTHER = "other"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    PAUSED = "paused"
    REMOVED = "removed"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    current_plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plans.id", ondelete="SET NULL"), default=None
    )
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[GoalCategory] = mapped_column(
        Enum(GoalCategory), default=GoalCategory.OTHER
    )
    target_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus), default=GoalStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PlanGoal(Base):
    __tablename__ = "plan_goals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("plans.id", ondelete="CASCADE")
    )
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="CASCADE")
    )
    funding_category: Mapped[NDISCategory] = mapped_column(
        Enum(NDISCategory), default=NDISCategory.CORE
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)


# ============================================================================
# Service agreements (Phase 2)
# ============================================================================


class AgreementStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ENDED = "ended"


class ServiceAgreement(Base):
    __tablename__ = "service_agreements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    service_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_types.id", ondelete="RESTRICT")
    )
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date, default=None)
    scope_notes: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[AgreementStatus] = mapped_column(
        Enum(AgreementStatus), default=AgreementStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


# ============================================================================
# Shifts (Phase 3) — scheduled / actual service delivery
# ============================================================================


class ShiftStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED_BY_PARTICIPANT = "cancelled_by_participant"
    CANCELLED_BY_PROVIDER = "cancelled_by_provider"
    NO_SHOW = "no_show"


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    staff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="SET NULL"), default=None
    )
    service_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_types.id", ondelete="RESTRICT")
    )
    service_agreement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("service_agreements.id", ondelete="SET NULL"),
        default=None,
    )
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    location: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[ShiftStatus] = mapped_column(
        Enum(ShiftStatus), default=ShiftStatus.SCHEDULED
    )
    cancelled_reason: Mapped[str | None] = mapped_column(Text, default=None)
    cancelled_by_staff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="SET NULL"), default=None
    )
    handover_note_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("progress_notes.id", use_alter=True,
                   name="fk_shifts_handover_note", ondelete="SET NULL"),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_shifts_participant_start", "participant_id", "scheduled_start"),
        Index("ix_shifts_staff_start", "staff_id", "scheduled_start"),
    )


# ============================================================================
# Progress notes (Phase 4) — immutable once locked
# ============================================================================


class ProgressNoteType(str, enum.Enum):
    SHIFT_NOTE = "shift_note"
    CLINICAL_OBSERVATION = "clinical_observation"
    FAMILY_COMMUNICATION = "family_communication"
    INCIDENT_RELATED = "incident_related"
    HANDOVER = "handover"
    GOAL_PROGRESS = "goal_progress"


class ProgressNote(Base):
    __tablename__ = "progress_notes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    author_staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    shift_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("shifts.id", ondelete="SET NULL"), default=None
    )
    incident_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("incidents.id", use_alter=True,
                   name="fk_progress_notes_incident", ondelete="SET NULL"),
        default=None,
    )
    note_type: Mapped[ProgressNoteType] = mapped_column(
        Enum(ProgressNoteType), default=ProgressNoteType.SHIFT_NOTE
    )
    content: Mapped[str] = mapped_column(Text)
    corrects_note_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("progress_notes.id", use_alter=True,
                   name="fk_progress_notes_corrects", ondelete="SET NULL"),
        default=None,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    locked_by_staff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_progress_notes_participant_created", "participant_id", "created_at"),
    )


# ============================================================================
# Incidents (Phase 4)
# ============================================================================


class IncidentType(str, enum.Enum):
    REPORTABLE = "reportable"
    GENERAL = "general"


class IncidentCategory(str, enum.Enum):
    ABUSE = "abuse"
    NEGLECT = "neglect"
    RESTRICTIVE_PRACTICE_UNAUTHORISED = "restrictive_practice_unauthorised"
    MEDICATION_ERROR = "medication_error"
    INJURY = "injury"
    NEAR_MISS = "near_miss"
    COMPLAINT = "complaint"
    BEHAVIOUR_CONCERN = "behaviour_concern"
    PROPERTY_DAMAGE = "property_damage"
    OTHER = "other"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="RESTRICT")
    )
    reporter_staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    shift_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("shifts.id", ondelete="SET NULL"), default=None
    )
    incident_type: Mapped[IncidentType] = mapped_column(
        Enum(IncidentType), default=IncidentType.GENERAL
    )
    category: Mapped[IncidentCategory] = mapped_column(
        Enum(IncidentCategory), default=IncidentCategory.OTHER
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(255), default=None)
    summary: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    immediate_action_taken: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.OPEN
    )
    ndis_commission_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    worksafe_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    police_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    notification_reference: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class IncidentFollowup(Base):
    __tablename__ = "incident_followups"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE")
    )
    staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    action_taken: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text, default=None)
    follow_up_due_date: Mapped[date | None] = mapped_column(Date, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Medications (Phase 4) — administration log is immutable
# ============================================================================


class MedicationRoute(str, enum.Enum):
    ORAL = "oral"
    TOPICAL = "topical"
    INJECTION = "injection"
    INHALATION = "inhalation"
    OTHER = "other"


class MedicationStatus(str, enum.Enum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"


class MedicationRecord(Base):
    __tablename__ = "medication_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    medication_name: Mapped[str] = mapped_column(String(255))
    dose: Mapped[str] = mapped_column(String(100))
    route: Mapped[MedicationRoute] = mapped_column(
        Enum(MedicationRoute), default=MedicationRoute.ORAL
    )
    frequency: Mapped[str] = mapped_column(String(100))
    prescriber: Mapped[str | None] = mapped_column(String(255), default=None)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    prn: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[MedicationStatus] = mapped_column(
        Enum(MedicationStatus), default=MedicationStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class MedicationAdministrationLog(Base):
    __tablename__ = "medication_administration_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    medication_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("medication_records.id", ondelete="RESTRICT")
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="RESTRICT")
    )
    administered_by_staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    shift_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("shifts.id", ondelete="SET NULL"), default=None
    )
    administered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dose_given: Mapped[str] = mapped_column(String(100))
    was_witnessed: Mapped[bool] = mapped_column(Boolean, default=False)
    witness_staff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="SET NULL"), default=None
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Restrictive practices (Phase 4)
# ============================================================================


class RestrictivePracticeType(str, enum.Enum):
    ENVIRONMENTAL = "environmental"
    CHEMICAL = "chemical"
    MECHANICAL = "mechanical"
    PHYSICAL = "physical"
    SECLUSION = "seclusion"
    NONE_AUTHORISED = "none_authorised"


class RestrictivePracticeStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RestrictivePractice(Base):
    __tablename__ = "restrictive_practices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    practice_type: Mapped[RestrictivePracticeType] = mapped_column(
        Enum(RestrictivePracticeType),
        default=RestrictivePracticeType.NONE_AUTHORISED,
    )
    authorisation_ref: Mapped[str | None] = mapped_column(String(255), default=None)
    authorised_from: Mapped[date | None] = mapped_column(Date, default=None)
    authorised_to: Mapped[date | None] = mapped_column(Date, default=None)
    behaviour_support_plan_doc_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id", use_alter=True,
                   name="fk_restrictive_bsp_doc", ondelete="SET NULL"),
        default=None,
    )
    status: Mapped[RestrictivePracticeStatus] = mapped_column(
        Enum(RestrictivePracticeStatus),
        default=RestrictivePracticeStatus.ACTIVE,
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ============================================================================
# Risk assessments (Phase 4)
# ============================================================================


class RiskAssessmentType(str, enum.Enum):
    MANUAL_HANDLING = "manual_handling"
    CHOKING = "choking"
    BEHAVIOURAL = "behavioural"
    ENVIRONMENTAL = "environmental"
    COMMUNITY_ACCESS = "community_access"
    MEDICATION = "medication"
    OTHER = "other"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    assessment_type: Mapped[RiskAssessmentType] = mapped_column(
        Enum(RiskAssessmentType), default=RiskAssessmentType.OTHER
    )
    level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.LOW)
    controls: Mapped[str] = mapped_column(Text)
    assessor_staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    review_due: Mapped[date | None] = mapped_column(Date, default=None)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("risk_assessments.id", use_alter=True,
                   name="fk_risk_superseded_by", ondelete="SET NULL"),
        default=None,
    )


# ============================================================================
# Participant preferences (Phase 4)
# ============================================================================


class PreferenceCategory(str, enum.Enum):
    COMMUNICATION = "communication"
    FOOD = "food"
    ROUTINE = "routine"
    SENSORY = "sensory"
    TRIGGER = "trigger"
    LIKE = "like"
    DISLIKE = "dislike"


class PreferencePriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"


class ParticipantPreference(Base):
    __tablename__ = "participant_preferences"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE")
    )
    category: Mapped[PreferenceCategory] = mapped_column(
        Enum(PreferenceCategory), default=PreferenceCategory.LIKE
    )
    detail: Mapped[str] = mapped_column(Text)
    priority: Mapped[PreferencePriority] = mapped_column(
        Enum(PreferencePriority), default=PreferencePriority.NORMAL
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Documents (Phase 4) — polymorphic pointer to S3/blob storage
# ============================================================================


class DocumentSubjectType(str, enum.Enum):
    PARTICIPANT = "participant"
    STAFF = "staff"


class DocumentType(str, enum.Enum):
    NDIS_PLAN = "ndis_plan"
    SERVICE_AGREEMENT = "service_agreement"
    CONSENT = "consent"
    ID_DOCUMENT = "id_document"
    MEDICAL = "medical"
    QUALIFICATION = "qualification"
    POLICE_CHECK = "police_check"
    WWCC = "wwcc"
    BEHAVIOUR_SUPPORT_PLAN = "behaviour_support_plan"
    RISK_ASSESSMENT = "risk_assessment"
    OTHER = "other"


# ============================================================================
# Auth — users + opaque session tokens
# ============================================================================


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    COORDINATOR = "coordinator"
    SUPPORT_WORKER = "support_worker"
    PARTICIPANT = "participant"


# Roles that grant access to global staff-facing views (dashboards, lists,
# knowledge editing, all participant records). Participant role is excluded.
STAFF_ROLES: frozenset[UserRole] = frozenset(
    {UserRole.ADMIN, UserRole.MANAGER, UserRole.COORDINATOR, UserRole.SUPPORT_WORKER}
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.SUPPORT_WORKER
    )
    staff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="SET NULL"), default=None
    )
    participant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="SET NULL"), default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    __table_args__ = (
        Index(
            "ix_users_email_live",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    __table_args__ = (Index("ix_auth_sessions_user", "user_id"),)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject_type: Mapped[DocumentSubjectType] = mapped_column(
        Enum(DocumentSubjectType), default=DocumentSubjectType.PARTICIPANT
    )
    subject_id: Mapped[str] = mapped_column(String(36))
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), default=DocumentType.OTHER
    )
    title: Mapped[str] = mapped_column(String(255))
    storage_url: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(100), default=None)
    size_bytes: Mapped[int | None] = mapped_column(Integer, default=None)
    uploaded_by_staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staff.id", ondelete="RESTRICT")
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    __table_args__ = (
        Index("ix_documents_subject", "subject_type", "subject_id"),
    )
