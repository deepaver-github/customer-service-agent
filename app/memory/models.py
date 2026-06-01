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
