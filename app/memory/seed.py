"""Seed the database with Special Care Australia sample data."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.auth.passwords import hash_password
from app.config import get_settings
from app.memory.database import init_db, get_session_factory
from app.memory.models import (
    AgreementStatus,
    AssignmentType,
    AustralianState,
    Contact,
    ContactRelationship,
    DisabilityCategory,
    Document,
    DocumentSubjectType,
    DocumentType,
    Goal,
    GoalCategory,
    GoalStatus,
    Incident,
    IncidentCategory,
    IncidentFollowup,
    IncidentStatus,
    IncidentType,
    KnowledgeArticle,
    KnowledgeCategory,
    KnowledgeStatus,
    MedicationAdministrationLog,
    MedicationRecord,
    MedicationRoute,
    MedicationStatus,
    NDISCategory,
    Participant,
    ParticipantPreference,
    ParticipantStaffAssignment,
    ParticipantStatus,
    Plan,
    PlanGoal,
    PlanManagementType,
    PlanStatus,
    PreferenceCategory,
    PreferencePriority,
    ProgressNote,
    ProgressNoteType,
    RestrictivePractice,
    RestrictivePracticeStatus,
    RestrictivePracticeType,
    RiskAssessment,
    RiskAssessmentType,
    RiskLevel,
    ServiceAgreement,
    ServiceType,
    ServiceTypeStatus,
    Shift,
    ShiftStatus,
    Staff,
    StaffRole,
    StaffStatus,
    User,
    UserRole,
)


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Participants (3) — IDs hardcoded so contacts/assignments can reference them.
# ---------------------------------------------------------------------------

PARTICIPANT_AISHA_ID = "aaaaaaaa-0001-4000-8000-000000000001"
PARTICIPANT_BEN_ID = "bbbbbbbb-0002-4000-8000-000000000002"
PARTICIPANT_CHLOE_ID = "cccccccc-0003-4000-8000-000000000003"

SEED_PARTICIPANTS = [
    Participant(
        id=PARTICIPANT_AISHA_ID,
        ndis_number="430112233",
        first_name="Aisha",
        last_name="Patel",
        preferred_name="Aisha",
        dob=date(1992, 4, 14),
        primary_disability_category=DisabilityCategory.PHYSICAL,
        communication_needs="Prefers SMS over phone. English only.",
        address_line1="14 Acacia Street",
        suburb="Parramatta",
        state=AustralianState.NSW,
        postcode="2150",
        phone="+61 412 555 101",
        email="aisha.p@example.com",
        status=ParticipantStatus.ACTIVE,
    ),
    Participant(
        id=PARTICIPANT_BEN_ID,
        ndis_number="430445566",
        first_name="Benjamin",
        last_name="Nguyen",
        preferred_name="Ben",
        dob=date(2005, 11, 2),
        primary_disability_category=DisabilityCategory.AUTISM,
        communication_needs=(
            "Uses AAC device for complex messages. "
            "Quiet environment helps with regulation."
        ),
        address_line1="6/22 Marine Parade",
        suburb="Coogee",
        state=AustralianState.NSW,
        postcode="2034",
        phone=None,
        email=None,
        status=ParticipantStatus.ACTIVE,
    ),
    Participant(
        id=PARTICIPANT_CHLOE_ID,
        ndis_number="430778899",
        first_name="Chloe",
        last_name="Ramirez",
        preferred_name="Chloe",
        dob=date(1968, 7, 30),
        primary_disability_category=DisabilityCategory.NEUROLOGICAL,
        communication_needs="Communicates verbally. Slow speech, allow time.",
        address_line1="3 Riverbend Drive",
        suburb="Penrith",
        state=AustralianState.NSW,
        postcode="2750",
        phone="+61 423 555 202",
        email="chloe.r@example.com",
        status=ParticipantStatus.ONBOARDING,
    ),
]


# ---------------------------------------------------------------------------
# Staff (2)
# ---------------------------------------------------------------------------

STAFF_MARIA_ID = "11111111-aaaa-4000-8000-000000000001"
STAFF_TOM_ID = "22222222-bbbb-4000-8000-000000000002"

SEED_STAFF = [
    Staff(
        id=STAFF_MARIA_ID,
        first_name="Maria",
        last_name="Lo",
        email="maria.lo@specialcareaust.example",
        phone="+61 411 555 001",
        role=StaffRole.COORDINATOR,
        ndis_worker_check_expiry=date(2027, 3, 1),
        wwcc_expiry=date(2028, 6, 15),
        police_check_expiry=date(2027, 1, 10),
        qualifications="Cert IV Disability; Mental Health First Aid",
        status=StaffStatus.ACTIVE,
    ),
    Staff(
        id=STAFF_TOM_ID,
        first_name="Tom",
        last_name="Schultz",
        email="tom.s@specialcareaust.example",
        phone="+61 411 555 002",
        role=StaffRole.SUPPORT_WORKER,
        ndis_worker_check_expiry=date(2026, 11, 20),
        wwcc_expiry=date(2027, 9, 1),
        police_check_expiry=date(2026, 10, 5),
        qualifications="Cert III Individual Support; manual-handling refresher 2026",
        status=StaffStatus.ACTIVE,
    ),
]


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

SEED_CONTACTS = [
    Contact(
        participant_id=PARTICIPANT_AISHA_ID,
        name="Priya Patel",
        relationship_type=ContactRelationship.FAMILY,
        phone="+61 412 555 102",
        email="priya.p@example.com",
        is_primary=True,
        is_emergency=True,
        notes="Sister. First point of contact.",
    ),
    Contact(
        participant_id=PARTICIPANT_AISHA_ID,
        name="Western Sydney Plan Management",
        relationship_type=ContactRelationship.PLAN_MANAGER,
        phone="+61 2 9000 4400",
        email="claims@wspm.example",
        is_primary=False,
        is_emergency=False,
        notes=None,
    ),
    Contact(
        participant_id=PARTICIPANT_BEN_ID,
        name="Linh Nguyen",
        relationship_type=ContactRelationship.GUARDIAN,
        phone="+61 412 555 103",
        email="linh.n@example.com",
        is_primary=True,
        is_emergency=True,
        notes="Mother and legal guardian.",
    ),
    Contact(
        participant_id=PARTICIPANT_BEN_ID,
        name="Dr Yusuf Khan",
        relationship_type=ContactRelationship.GP,
        phone="+61 2 9555 2200",
        email=None,
        is_primary=False,
        is_emergency=False,
        notes="Coogee Medical Centre.",
    ),
    Contact(
        participant_id=PARTICIPANT_CHLOE_ID,
        name="James Ramirez",
        relationship_type=ContactRelationship.FAMILY,
        phone="+61 423 555 203",
        email="james.r@example.com",
        is_primary=True,
        is_emergency=True,
        notes="Husband. Lives at same address.",
    ),
    Contact(
        participant_id=PARTICIPANT_CHLOE_ID,
        name="Penrith LAC",
        relationship_type=ContactRelationship.SUPPORT_COORDINATOR,
        phone="+61 2 4700 1000",
        email="lac.penrith@example.org",
        is_primary=False,
        is_emergency=False,
        notes="Local Area Coordinator during onboarding.",
    ),
]


# ---------------------------------------------------------------------------
# Participant ↔ Staff assignments
# ---------------------------------------------------------------------------

SEED_ASSIGNMENTS = [
    ParticipantStaffAssignment(
        participant_id=PARTICIPANT_AISHA_ID,
        staff_id=STAFF_MARIA_ID,
        assignment_type=AssignmentType.PRIMARY,
        valid_from=date(2025, 1, 15),
        notes="Coordinator since onboarding.",
    ),
    ParticipantStaffAssignment(
        participant_id=PARTICIPANT_AISHA_ID,
        staff_id=STAFF_TOM_ID,
        assignment_type=AssignmentType.PRIMARY,
        valid_from=date(2025, 2, 1),
        notes="Primary support worker, weekday mornings.",
    ),
    ParticipantStaffAssignment(
        participant_id=PARTICIPANT_BEN_ID,
        staff_id=STAFF_TOM_ID,
        assignment_type=AssignmentType.PRIMARY,
        valid_from=date(2025, 6, 1),
        notes="Community participation supports.",
    ),
    ParticipantStaffAssignment(
        participant_id=PARTICIPANT_CHLOE_ID,
        staff_id=STAFF_MARIA_ID,
        assignment_type=AssignmentType.PRIMARY,
        valid_from=date(2026, 5, 20),
        notes="Onboarding coordinator.",
    ),
]


# ---------------------------------------------------------------------------
# Service catalog
# ---------------------------------------------------------------------------

SEED_SERVICE_TYPES = [
    ServiceType(
        code="sil",
        name="Supported Independent Living (SIL)",
        description=(
            "Help with day-to-day tasks in a participant's home so they can "
            "live as independently as possible. Includes overnight supports."
        ),
        ndis_category=NDISCategory.CORE,
        status=ServiceTypeStatus.ACTIVE,
    ),
    ServiceType(
        code="personal_care",
        name="Daily Personal Care",
        description=(
            "Assistance with personal hygiene, dressing, meal preparation "
            "and other activities of daily living."
        ),
        ndis_category=NDISCategory.CORE,
        status=ServiceTypeStatus.ACTIVE,
    ),
    ServiceType(
        code="community_participation",
        name="Community Participation",
        description=(
            "Support to take part in community, social, and recreational "
            "activities outside the home."
        ),
        ndis_category=NDISCategory.CORE,
        status=ServiceTypeStatus.ACTIVE,
    ),
    ServiceType(
        code="respite",
        name="Short-Term Accommodation & Respite",
        description=(
            "Short stays away from home that give participants a change of "
            "scene and give families a break."
        ),
        ndis_category=NDISCategory.CORE,
        status=ServiceTypeStatus.ACTIVE,
    ),
    ServiceType(
        code="complex_support",
        name="Complex Disability Support",
        description=(
            "Higher-intensity supports for participants with complex needs, "
            "including behaviour support and clinical oversight."
        ),
        ndis_category=NDISCategory.CAPACITY_BUILDING,
        status=ServiceTypeStatus.ACTIVE,
    ),
]


# ---------------------------------------------------------------------------
# Knowledge articles (replaces FAQs)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Plans — one active per participant
# ---------------------------------------------------------------------------

PLAN_AISHA_ID = "11aaaaaa-0001-4000-8000-000000000001"
PLAN_BEN_ID = "11bbbbbb-0001-4000-8000-000000000002"
PLAN_CHLOE_ID = "11cccccc-0001-4000-8000-000000000003"

SEED_PLANS = [
    Plan(
        id=PLAN_AISHA_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        plan_number="P-AISHA-2025",
        start_date=date(2025, 1, 15),
        end_date=date(2026, 1, 14),
        management_type=PlanManagementType.PLAN_MANAGED,
        plan_manager_name="Western Sydney Plan Management",
        plan_manager_contact="claims@wspm.example",
        status=PlanStatus.ACTIVE,
    ),
    Plan(
        id=PLAN_BEN_ID,
        participant_id=PARTICIPANT_BEN_ID,
        plan_number="P-BEN-2025",
        start_date=date(2025, 6, 1),
        end_date=date(2026, 5, 31),
        management_type=PlanManagementType.AGENCY_MANAGED,
        plan_manager_name=None,
        plan_manager_contact=None,
        status=PlanStatus.ACTIVE,
    ),
    Plan(
        id=PLAN_CHLOE_ID,
        participant_id=PARTICIPANT_CHLOE_ID,
        plan_number="P-CHLOE-2026",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
        management_type=PlanManagementType.SELF,
        plan_manager_name=None,
        plan_manager_contact=None,
        status=PlanStatus.DRAFT,
    ),
]


# ---------------------------------------------------------------------------
# Goals — belong to participant, optionally point at current plan
# ---------------------------------------------------------------------------

GOAL_AISHA_INDEP_ID = "22aaaaaa-0001-4000-8000-000000000001"
GOAL_AISHA_COMM_ID = "22aaaaaa-0002-4000-8000-000000000002"
GOAL_BEN_LEARN_ID = "22bbbbbb-0001-4000-8000-000000000003"
GOAL_BEN_COMM_ID = "22bbbbbb-0002-4000-8000-000000000004"
GOAL_CHLOE_HEALTH_ID = "22cccccc-0001-4000-8000-000000000005"

SEED_GOALS = [
    Goal(
        id=GOAL_AISHA_INDEP_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        current_plan_id=PLAN_AISHA_ID,
        description="Maintain independent living in current home with morning supports.",
        category=GoalCategory.INDEPENDENCE,
        target_date=date(2026, 1, 14),
        status=GoalStatus.ACTIVE,
    ),
    Goal(
        id=GOAL_AISHA_COMM_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        current_plan_id=PLAN_AISHA_ID,
        description="Attend community art group at Parramatta library weekly.",
        category=GoalCategory.COMMUNITY,
        target_date=None,
        status=GoalStatus.ACTIVE,
    ),
    Goal(
        id=GOAL_BEN_LEARN_ID,
        participant_id=PARTICIPANT_BEN_ID,
        current_plan_id=PLAN_BEN_ID,
        description="Build communication skills using AAC device in everyday settings.",
        category=GoalCategory.LEARNING,
        target_date=date(2026, 5, 31),
        status=GoalStatus.ACTIVE,
    ),
    Goal(
        id=GOAL_BEN_COMM_ID,
        participant_id=PARTICIPANT_BEN_ID,
        current_plan_id=PLAN_BEN_ID,
        description="Participate in two community outings per month with support worker.",
        category=GoalCategory.COMMUNITY,
        target_date=None,
        status=GoalStatus.ACTIVE,
    ),
    Goal(
        id=GOAL_CHLOE_HEALTH_ID,
        participant_id=PARTICIPANT_CHLOE_ID,
        current_plan_id=PLAN_CHLOE_ID,
        description="Establish daily routine for medication and physiotherapy exercises.",
        category=GoalCategory.HEALTH,
        target_date=None,
        status=GoalStatus.ACTIVE,
    ),
]


# ---------------------------------------------------------------------------
# plan_goals join — every goal currently funded under the matching plan
# ---------------------------------------------------------------------------

SEED_PLAN_GOALS = [
    PlanGoal(plan_id=PLAN_AISHA_ID, goal_id=GOAL_AISHA_INDEP_ID,
             funding_category=NDISCategory.CORE, priority=1),
    PlanGoal(plan_id=PLAN_AISHA_ID, goal_id=GOAL_AISHA_COMM_ID,
             funding_category=NDISCategory.CORE, priority=2),
    PlanGoal(plan_id=PLAN_BEN_ID, goal_id=GOAL_BEN_LEARN_ID,
             funding_category=NDISCategory.CAPACITY_BUILDING, priority=1),
    PlanGoal(plan_id=PLAN_BEN_ID, goal_id=GOAL_BEN_COMM_ID,
             funding_category=NDISCategory.CORE, priority=2),
    PlanGoal(plan_id=PLAN_CHLOE_ID, goal_id=GOAL_CHLOE_HEALTH_ID,
             funding_category=NDISCategory.CAPACITY_BUILDING, priority=1),
]


# ---------------------------------------------------------------------------
# Service agreements — what SCA has agreed to deliver per participant.
# IDs are resolved at seed time because service_types.id is generated.
# ---------------------------------------------------------------------------


def _build_service_agreements(service_type_by_code: dict[str, ServiceType]) -> list[ServiceAgreement]:
    return [
        ServiceAgreement(
            participant_id=PARTICIPANT_AISHA_ID,
            service_type_id=service_type_by_code["personal_care"].id,
            valid_from=date(2025, 2, 1),
            valid_to=date(2026, 1, 14),
            scope_notes="Morning routine support, weekdays.",
            status=AgreementStatus.ACTIVE,
        ),
        ServiceAgreement(
            participant_id=PARTICIPANT_AISHA_ID,
            service_type_id=service_type_by_code["community_participation"].id,
            valid_from=date(2025, 3, 1),
            valid_to=date(2026, 1, 14),
            scope_notes="Weekly community group attendance.",
            status=AgreementStatus.ACTIVE,
        ),
        ServiceAgreement(
            participant_id=PARTICIPANT_BEN_ID,
            service_type_id=service_type_by_code["community_participation"].id,
            valid_from=date(2025, 6, 15),
            valid_to=date(2026, 5, 31),
            scope_notes="Two outings per month plus AAC practice in community.",
            status=AgreementStatus.ACTIVE,
        ),
        ServiceAgreement(
            participant_id=PARTICIPANT_CHLOE_ID,
            service_type_id=service_type_by_code["personal_care"].id,
            valid_from=date(2026, 6, 1),
            valid_to=None,
            scope_notes="Onboarding — draft pending signature.",
            status=AgreementStatus.DRAFT,
        ),
    ]


SEED_KNOWLEDGE = [
    KnowledgeArticle(
        title="What services does Special Care Australia offer?",
        body_md=(
            "We're an NDIS-registered provider supporting people across NSW. "
            "Our core services are **Supported Independent Living (SIL)**, "
            "**daily personal care**, **community participation**, "
            "**short-term accommodation and respite**, and **complex "
            "disability support**.\n\n"
            "If you're not sure which is the right fit, get in touch and a "
            "coordinator will help you work it out."
        ),
        category=KnowledgeCategory.ABOUT_SERVICES,
        tags=["sil", "personal_care", "respite", "overview"],
        status=KnowledgeStatus.PUBLISHED,
    ),
    KnowledgeArticle(
        title="How do I start receiving supports from Special Care Australia?",
        body_md=(
            "1. Get in touch — phone, email, or via this chat.\n"
            "2. We'll arrange a free intake conversation with a coordinator.\n"
            "3. Together we go through your NDIS plan and what you'd like "
            "support with.\n"
            "4. We draft a **service agreement** describing the supports, "
            "hours, and any specific preferences.\n"
            "5. Once you've signed, we roster a support worker who's a good "
            "match and your supports begin."
        ),
        category=KnowledgeCategory.GETTING_STARTED,
        tags=["intake", "onboarding", "service_agreement"],
        status=KnowledgeStatus.PUBLISHED,
    ),
    KnowledgeArticle(
        title="How are NDIS plans managed?",
        body_md=(
            "Your NDIS plan can be managed in one of three ways:\n\n"
            "- **Self-managed** — you (or a nominee) handle invoices and "
            "payments directly.\n"
            "- **Plan-managed** — a registered plan manager handles "
            "payments on your behalf. You stay in control of choices.\n"
            "- **Agency-managed** — the NDIA pays providers directly. You "
            "can only use NDIS-registered providers.\n\n"
            "Special Care Australia is an NDIS-registered provider, so we "
            "work with all three. If you're not sure how your plan is "
            "managed, your plan document or LAC can confirm."
        ),
        category=KnowledgeCategory.NDIS_BASICS,
        tags=["plan_management", "self_managed", "plan_managed", "agency_managed"],
        status=KnowledgeStatus.PUBLISHED,
    ),
    KnowledgeArticle(
        title="What is Supported Independent Living (SIL)?",
        body_md=(
            "SIL is help with day-to-day tasks in your own home so you can "
            "live as independently as possible. Supports might include "
            "personal care, meal preparation, medication prompts, household "
            "tasks, and overnight assistance.\n\n"
            "SIL is funded under the **Core** support budget in your NDIS "
            "plan. It's separate from the cost of the home itself "
            "(rent/utilities)."
        ),
        category=KnowledgeCategory.SUPPORTS_EXPLAINED,
        tags=["sil", "core_supports"],
        status=KnowledgeStatus.PUBLISHED,
    ),
    KnowledgeArticle(
        title="How do I make a complaint or give feedback?",
        body_md=(
            "We take complaints seriously — they help us improve.\n\n"
            "**To raise something with us directly:** speak to your "
            "coordinator, call the office, or email "
            "**feedback@specialcareaust.example**. We aim to acknowledge "
            "complaints within 2 business days.\n\n"
            "**External options:** you can also contact the NDIS Quality "
            "and Safeguards Commission on **1800 035 544** or via "
            "ndiscommission.gov.au. Using one doesn't stop you using the "
            "other."
        ),
        category=KnowledgeCategory.COMPLAINTS_FEEDBACK,
        tags=["complaints", "feedback", "ndis_commission"],
        status=KnowledgeStatus.PUBLISHED,
    ),
    KnowledgeArticle(
        title="What is a service agreement and why do I need one?",
        body_md=(
            "A service agreement is a written agreement between you and "
            "Special Care Australia describing the supports we'll provide.\n\n"
            "It covers:\n"
            "- which supports (e.g. personal care, community participation)\n"
            "- how often\n"
            "- the period it covers\n"
            "- cancellation and feedback processes\n\n"
            "You can ask for changes at any time. Both parties sign before "
            "supports begin."
        ),
        category=KnowledgeCategory.GETTING_STARTED,
        tags=["service_agreement", "onboarding"],
        status=KnowledgeStatus.PUBLISHED,
    ),
]


# ---------------------------------------------------------------------------
# Phase 3 — Shifts. IDs resolved at seed time once service_types have IDs.
# ---------------------------------------------------------------------------

SHIFT_AISHA_PAST_1_ID = "33aaaaaa-0001-4000-8000-000000000001"
SHIFT_AISHA_PAST_2_ID = "33aaaaaa-0002-4000-8000-000000000002"
SHIFT_AISHA_UPCOMING_ID = "33aaaaaa-0003-4000-8000-000000000003"
SHIFT_AISHA_CANCELLED_ID = "33aaaaaa-0004-4000-8000-000000000004"
SHIFT_BEN_PAST_ID = "33bbbbbb-0001-4000-8000-000000000005"
SHIFT_BEN_UPCOMING_ID = "33bbbbbb-0002-4000-8000-000000000006"


def _build_shifts(service_type_by_code: dict[str, ServiceType]) -> list[Shift]:
    sil = service_type_by_code["personal_care"].id
    comm = service_type_by_code["community_participation"].id
    return [
        # Aisha — past, completed
        Shift(
            id=SHIFT_AISHA_PAST_1_ID,
            participant_id=PARTICIPANT_AISHA_ID,
            staff_id=STAFF_TOM_ID,
            service_type_id=sil,
            scheduled_start=_utc(2026, 5, 25, 9, 0),
            scheduled_end=_utc(2026, 5, 25, 11, 0),
            actual_start=_utc(2026, 5, 25, 9, 5),
            actual_end=_utc(2026, 5, 25, 11, 0),
            location="14 Acacia Street, Parramatta NSW 2150",
            status=ShiftStatus.COMPLETED,
        ),
        Shift(
            id=SHIFT_AISHA_PAST_2_ID,
            participant_id=PARTICIPANT_AISHA_ID,
            staff_id=STAFF_TOM_ID,
            service_type_id=sil,
            scheduled_start=_utc(2026, 5, 30, 9, 0),
            scheduled_end=_utc(2026, 5, 30, 11, 0),
            actual_start=_utc(2026, 5, 30, 9, 0),
            actual_end=_utc(2026, 5, 30, 10, 55),
            location="14 Acacia Street, Parramatta NSW 2150",
            status=ShiftStatus.COMPLETED,
        ),
        # Aisha — upcoming
        Shift(
            id=SHIFT_AISHA_UPCOMING_ID,
            participant_id=PARTICIPANT_AISHA_ID,
            staff_id=STAFF_TOM_ID,
            service_type_id=sil,
            scheduled_start=_utc(2026, 6, 5, 9, 0),
            scheduled_end=_utc(2026, 6, 5, 11, 0),
            location="14 Acacia Street, Parramatta NSW 2150",
            status=ShiftStatus.SCHEDULED,
        ),
        # Aisha — cancelled
        Shift(
            id=SHIFT_AISHA_CANCELLED_ID,
            participant_id=PARTICIPANT_AISHA_ID,
            staff_id=STAFF_TOM_ID,
            service_type_id=comm,
            scheduled_start=_utc(2026, 5, 28, 11, 0),
            scheduled_end=_utc(2026, 5, 28, 13, 0),
            location="Parramatta Library",
            status=ShiftStatus.CANCELLED_BY_PARTICIPANT,
            cancelled_reason="Unwell, rescheduled by SMS.",
            cancelled_by_staff_id=STAFF_MARIA_ID,
        ),
        # Ben — past completed
        Shift(
            id=SHIFT_BEN_PAST_ID,
            participant_id=PARTICIPANT_BEN_ID,
            staff_id=STAFF_TOM_ID,
            service_type_id=comm,
            scheduled_start=_utc(2026, 5, 22, 14, 0),
            scheduled_end=_utc(2026, 5, 22, 17, 0),
            actual_start=_utc(2026, 5, 22, 14, 10),
            actual_end=_utc(2026, 5, 22, 17, 0),
            location="Coogee Beach foreshore",
            status=ShiftStatus.COMPLETED,
        ),
        # Ben — upcoming
        Shift(
            id=SHIFT_BEN_UPCOMING_ID,
            participant_id=PARTICIPANT_BEN_ID,
            staff_id=STAFF_TOM_ID,
            service_type_id=comm,
            scheduled_start=_utc(2026, 6, 7, 14, 0),
            scheduled_end=_utc(2026, 6, 7, 17, 0),
            location="Sydney Aquarium",
            status=ShiftStatus.SCHEDULED,
        ),
    ]


# ---------------------------------------------------------------------------
# Phase 4 — Progress notes (locked + immutable)
# ---------------------------------------------------------------------------

NOTE_AISHA_HANDOVER_ID = "44aaaaaa-0001-4000-8000-000000000001"
NOTE_AISHA_SHIFT_ID = "44aaaaaa-0002-4000-8000-000000000002"
NOTE_BEN_GOAL_ID = "44bbbbbb-0001-4000-8000-000000000003"

SEED_PROGRESS_NOTES = [
    ProgressNote(
        id=NOTE_AISHA_HANDOVER_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        author_staff_id=STAFF_TOM_ID,
        shift_id=SHIFT_AISHA_PAST_1_ID,
        note_type=ProgressNoteType.HANDOVER,
        content=(
            "Aisha in good spirits this morning. Completed her morning routine "
            "with prompting. Reminded her about Friday's community art group. "
            "Left meal prepared in fridge for lunch."
        ),
        locked_at=_utc(2026, 5, 25, 11, 30),
        locked_by_staff_id=STAFF_TOM_ID,
    ),
    ProgressNote(
        id=NOTE_AISHA_SHIFT_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        author_staff_id=STAFF_TOM_ID,
        shift_id=SHIFT_AISHA_PAST_2_ID,
        note_type=ProgressNoteType.SHIFT_NOTE,
        content=(
            "Routine personal care delivered. Aisha mentioned slight shoulder "
            "stiffness — recommended she mention to her GP at next visit."
        ),
        locked_at=_utc(2026, 5, 30, 11, 15),
        locked_by_staff_id=STAFF_TOM_ID,
    ),
    ProgressNote(
        id=NOTE_BEN_GOAL_ID,
        participant_id=PARTICIPANT_BEN_ID,
        author_staff_id=STAFF_TOM_ID,
        shift_id=SHIFT_BEN_PAST_ID,
        note_type=ProgressNoteType.GOAL_PROGRESS,
        content=(
            "Ben used his AAC device confidently to order an ice cream "
            "independently — first time. Repeated success at the kiosk later. "
            "Linh notified by SMS — delighted."
        ),
        locked_at=_utc(2026, 5, 22, 17, 30),
        locked_by_staff_id=STAFF_TOM_ID,
    ),
]


# ---------------------------------------------------------------------------
# Phase 4 — Incidents + follow-ups
# ---------------------------------------------------------------------------

INCIDENT_AISHA_NEAR_MISS_ID = "55aaaaaa-0001-4000-8000-000000000001"

SEED_INCIDENTS = [
    Incident(
        id=INCIDENT_AISHA_NEAR_MISS_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        reporter_staff_id=STAFF_TOM_ID,
        shift_id=SHIFT_AISHA_PAST_1_ID,
        incident_type=IncidentType.GENERAL,
        category=IncidentCategory.NEAR_MISS,
        occurred_at=_utc(2026, 5, 25, 10, 30),
        location="14 Acacia Street, kitchen",
        summary="Wet kitchen floor — no fall.",
        description=(
            "Kettle had leaked, leaving a small puddle in front of the sink. "
            "Aisha noticed before walking through; Tom dried the floor and "
            "placed a hazard sign. No injury, no fall."
        ),
        immediate_action_taken=(
            "Floor dried, hazard sign placed, kettle replaced. Aisha confirmed "
            "she is comfortable."
        ),
        status=IncidentStatus.CLOSED,
    ),
]

SEED_INCIDENT_FOLLOWUPS = [
    IncidentFollowup(
        incident_id=INCIDENT_AISHA_NEAR_MISS_ID,
        staff_id=STAFF_MARIA_ID,
        action_taken="Replacement kettle delivered and tested. Confirmed no recurrence.",
        outcome="No further issues; incident closed.",
        follow_up_due_date=date(2026, 6, 1),
        completed_at=_utc(2026, 5, 31, 14, 0),
    ),
]


# ---------------------------------------------------------------------------
# Phase 4 — Medications
# ---------------------------------------------------------------------------

MED_AISHA_BACLOFEN_ID = "66aaaaaa-0001-4000-8000-000000000001"
MED_AISHA_PRN_PARACETAMOL_ID = "66aaaaaa-0002-4000-8000-000000000002"
MED_CHLOE_LEVODOPA_ID = "66cccccc-0001-4000-8000-000000000003"

SEED_MEDICATIONS = [
    MedicationRecord(
        id=MED_AISHA_BACLOFEN_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        medication_name="Baclofen",
        dose="10 mg",
        route=MedicationRoute.ORAL,
        frequency="Three times daily with food",
        prescriber="Dr Helena Cross, Westmead Rehab",
        start_date=date(2024, 8, 1),
        prn=False,
        notes="Long-term spasticity management.",
        status=MedicationStatus.ACTIVE,
    ),
    MedicationRecord(
        id=MED_AISHA_PRN_PARACETAMOL_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        medication_name="Paracetamol",
        dose="500 mg",
        route=MedicationRoute.ORAL,
        frequency="PRN for pain, max 4 doses / 24h",
        prescriber="GP — Dr Anh Tran",
        start_date=date(2025, 1, 1),
        prn=True,
        notes="Aisha to self-administer. Worker prompts only.",
        status=MedicationStatus.ACTIVE,
    ),
    MedicationRecord(
        id=MED_CHLOE_LEVODOPA_ID,
        participant_id=PARTICIPANT_CHLOE_ID,
        medication_name="Levodopa/Carbidopa",
        dose="100/25 mg",
        route=MedicationRoute.ORAL,
        frequency="Four times daily",
        prescriber="Dr P. Singh, neurology",
        start_date=date(2023, 3, 15),
        prn=False,
        notes="Pending review at next neurology visit.",
        status=MedicationStatus.ACTIVE,
    ),
]

SEED_MED_ADMIN_LOG = [
    MedicationAdministrationLog(
        medication_record_id=MED_AISHA_BACLOFEN_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        administered_by_staff_id=STAFF_TOM_ID,
        shift_id=SHIFT_AISHA_PAST_1_ID,
        administered_at=_utc(2026, 5, 25, 9, 30),
        dose_given="10 mg",
        was_witnessed=False,
        notes="Morning dose taken with breakfast.",
    ),
    MedicationAdministrationLog(
        medication_record_id=MED_AISHA_BACLOFEN_ID,
        participant_id=PARTICIPANT_AISHA_ID,
        administered_by_staff_id=STAFF_TOM_ID,
        shift_id=SHIFT_AISHA_PAST_2_ID,
        administered_at=_utc(2026, 5, 30, 9, 25),
        dose_given="10 mg",
        was_witnessed=False,
    ),
]


# ---------------------------------------------------------------------------
# Phase 4 — Restrictive practices
# ---------------------------------------------------------------------------

SEED_RESTRICTIVE_PRACTICES = [
    RestrictivePractice(
        participant_id=PARTICIPANT_BEN_ID,
        practice_type=RestrictivePracticeType.NONE_AUTHORISED,
        authorisation_ref=None,
        authorised_from=None,
        authorised_to=None,
        status=RestrictivePracticeStatus.ACTIVE,
        notes=(
            "No restrictive practices currently authorised. Behaviour support "
            "plan in place focuses on positive behaviour support and sensory "
            "regulation."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Phase 4 — Risk assessments
# ---------------------------------------------------------------------------

SEED_RISK_ASSESSMENTS = [
    RiskAssessment(
        participant_id=PARTICIPANT_AISHA_ID,
        assessment_type=RiskAssessmentType.MANUAL_HANDLING,
        level=RiskLevel.MEDIUM,
        controls=(
            "Transfer board used for shower transfer. Two-person assist not "
            "required. Worker to follow manual handling refresher."
        ),
        assessor_staff_id=STAFF_MARIA_ID,
        assessed_at=_utc(2026, 2, 1, 10, 0),
        review_due=date(2027, 2, 1),
    ),
    RiskAssessment(
        participant_id=PARTICIPANT_BEN_ID,
        assessment_type=RiskAssessmentType.COMMUNITY_ACCESS,
        level=RiskLevel.MEDIUM,
        controls=(
            "Always have AAC device, water, and noise-cancelling headphones. "
            "Avoid crowded venues during peak hours. Plan quiet exit route."
        ),
        assessor_staff_id=STAFF_MARIA_ID,
        assessed_at=_utc(2026, 3, 5, 11, 0),
        review_due=date(2027, 3, 5),
    ),
]


# ---------------------------------------------------------------------------
# Phase 4 — Preferences
# ---------------------------------------------------------------------------

SEED_PREFERENCES = [
    ParticipantPreference(
        participant_id=PARTICIPANT_AISHA_ID,
        category=PreferenceCategory.COMMUNICATION,
        priority=PreferencePriority.HIGH,
        detail="Prefers SMS for reminders. Phone calls only if urgent.",
    ),
    ParticipantPreference(
        participant_id=PARTICIPANT_AISHA_ID,
        category=PreferenceCategory.LIKE,
        priority=PreferencePriority.NORMAL,
        detail="Loves Sri Lankan tea (strong, no sugar). Pottery and art classes.",
    ),
    ParticipantPreference(
        participant_id=PARTICIPANT_AISHA_ID,
        category=PreferenceCategory.ROUTINE,
        priority=PreferencePriority.HIGH,
        detail="Morning routine: medication, shower, breakfast, then plan the day.",
    ),
    ParticipantPreference(
        participant_id=PARTICIPANT_BEN_ID,
        category=PreferenceCategory.COMMUNICATION,
        priority=PreferencePriority.CRITICAL,
        detail="Uses AAC device. Allow extra processing time after questions.",
    ),
    ParticipantPreference(
        participant_id=PARTICIPANT_BEN_ID,
        category=PreferenceCategory.SENSORY,
        priority=PreferencePriority.HIGH,
        detail="Headphones for loud venues. Sunglasses outdoors in summer.",
    ),
    ParticipantPreference(
        participant_id=PARTICIPANT_BEN_ID,
        category=PreferenceCategory.TRIGGER,
        priority=PreferencePriority.CRITICAL,
        detail=(
            "Surprise changes to plan cause distress. Always preview new venues "
            "and schedule changes the day before."
        ),
    ),
    ParticipantPreference(
        participant_id=PARTICIPANT_CHLOE_ID,
        category=PreferenceCategory.COMMUNICATION,
        priority=PreferencePriority.HIGH,
        detail="Speech is slow — wait without finishing her sentences.",
    ),
]


# ---------------------------------------------------------------------------
# Phase 4 — Documents (storage_url is a placeholder pointer)
# ---------------------------------------------------------------------------

SEED_DOCUMENTS = [
    Document(
        subject_type=DocumentSubjectType.PARTICIPANT,
        subject_id=PARTICIPANT_AISHA_ID,
        document_type=DocumentType.NDIS_PLAN,
        title="Aisha Patel — NDIS Plan 2025",
        storage_url="placeholder://documents/aisha-ndis-plan-2025.pdf",
        mime_type="application/pdf",
        size_bytes=412_000,
        uploaded_by_staff_id=STAFF_MARIA_ID,
    ),
    Document(
        subject_type=DocumentSubjectType.PARTICIPANT,
        subject_id=PARTICIPANT_BEN_ID,
        document_type=DocumentType.BEHAVIOUR_SUPPORT_PLAN,
        title="Benjamin Nguyen — Positive Behaviour Support Plan",
        storage_url="placeholder://documents/ben-bsp.pdf",
        mime_type="application/pdf",
        size_bytes=580_000,
        uploaded_by_staff_id=STAFF_MARIA_ID,
    ),
    Document(
        subject_type=DocumentSubjectType.STAFF,
        subject_id=STAFF_TOM_ID,
        document_type=DocumentType.WWCC,
        title="Tom Schultz — WWCC scan",
        storage_url="placeholder://documents/tom-wwcc.pdf",
        mime_type="application/pdf",
        size_bytes=120_000,
        uploaded_by_staff_id=STAFF_MARIA_ID,
        expiry_date=date(2027, 9, 1),
    ),
]


# ---------------------------------------------------------------------------
# Auth — default users. All seed accounts share a known dev password; the
# admin password is printed at seed time so it's hard to miss.
# ---------------------------------------------------------------------------

SEED_DEV_PASSWORD = "ChangeMe!2026"  # dev/test only — rotate before any real data lands


def _build_users() -> list[User]:
    pw = hash_password(SEED_DEV_PASSWORD)
    return [
        # Admin — not linked to any staff/participant row.
        User(
            email="admin@specialcareaust.example",
            password_hash=pw,
            role=UserRole.ADMIN,
        ),
        # Staff users — linked to the seeded staff rows.
        User(
            email="maria.lo@specialcareaust.example",
            password_hash=pw,
            role=UserRole.COORDINATOR,
            staff_id=STAFF_MARIA_ID,
        ),
        User(
            email="tom.s@specialcareaust.example",
            password_hash=pw,
            role=UserRole.SUPPORT_WORKER,
            staff_id=STAFF_TOM_ID,
        ),
        # Participant self-service users — linked to participant rows.
        User(
            email="aisha.p@example.com",
            password_hash=pw,
            role=UserRole.PARTICIPANT,
            participant_id=PARTICIPANT_AISHA_ID,
        ),
        User(
            email="ben.n@example.com",
            password_hash=pw,
            role=UserRole.PARTICIPANT,
            participant_id=PARTICIPANT_BEN_ID,
        ),
        User(
            email="chloe.r@example.com",
            password_hash=pw,
            role=UserRole.PARTICIPANT,
            participant_id=PARTICIPANT_CHLOE_ID,
        ),
    ]


async def seed() -> None:
    settings = get_settings()
    await init_db(settings.database_url)

    async with get_session_factory()() as db:
        existing = await db.execute(select(Participant).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Database already seeded — skipping.")
            return

        # Parents first (participants + staff + service catalog), flush so their
        # generated IDs are visible, then children that reference them.
        for row in SEED_PARTICIPANTS:
            db.add(row)
        for row in SEED_STAFF:
            db.add(row)
        for row in SEED_SERVICE_TYPES:
            db.add(row)
        for row in SEED_KNOWLEDGE:
            db.add(row)
        await db.flush()

        for row in SEED_CONTACTS:
            db.add(row)
        for row in SEED_ASSIGNMENTS:
            db.add(row)
        for row in SEED_PLANS:
            db.add(row)
        await db.flush()

        for row in SEED_GOALS:
            db.add(row)
        await db.flush()

        for row in SEED_PLAN_GOALS:
            db.add(row)

        service_type_by_code = {st.code: st for st in SEED_SERVICE_TYPES}
        seed_agreements = _build_service_agreements(service_type_by_code)
        for row in seed_agreements:
            db.add(row)

        # Phase 3 — shifts depend on service_types having IDs.
        seed_shifts = _build_shifts(service_type_by_code)
        for row in seed_shifts:
            db.add(row)
        await db.flush()

        # Phase 4 — clinical / safeguarding.
        for row in SEED_PROGRESS_NOTES:
            db.add(row)
        for row in SEED_INCIDENTS:
            db.add(row)
        for row in SEED_MEDICATIONS:
            db.add(row)
        await db.flush()

        for row in SEED_INCIDENT_FOLLOWUPS:
            db.add(row)
        for row in SEED_MED_ADMIN_LOG:
            db.add(row)
        for row in SEED_RESTRICTIVE_PRACTICES:
            db.add(row)
        for row in SEED_RISK_ASSESSMENTS:
            db.add(row)
        for row in SEED_PREFERENCES:
            db.add(row)
        for row in SEED_DOCUMENTS:
            db.add(row)
        await db.flush()

        # Wire the handover note back to its shift (bidirectional pointer).
        first_shift = await db.get(Shift, SHIFT_AISHA_PAST_1_ID)
        if first_shift is not None:
            first_shift.handover_note_id = NOTE_AISHA_HANDOVER_ID

        # Auth users (staff_id/participant_id FKs already exist after the flushes above).
        seed_users = _build_users()
        for row in seed_users:
            db.add(row)

        await db.commit()
        print(
            f"Seeded: {len(SEED_PARTICIPANTS)} participants, "
            f"{len(SEED_STAFF)} staff, "
            f"{len(SEED_CONTACTS)} contacts, "
            f"{len(SEED_ASSIGNMENTS)} assignments, "
            f"{len(SEED_SERVICE_TYPES)} service types, "
            f"{len(SEED_KNOWLEDGE)} knowledge articles, "
            f"{len(SEED_PLANS)} plans, "
            f"{len(SEED_GOALS)} goals, "
            f"{len(SEED_PLAN_GOALS)} plan-goal links, "
            f"{len(seed_agreements)} service agreements, "
            f"{len(seed_shifts)} shifts, "
            f"{len(SEED_PROGRESS_NOTES)} progress notes, "
            f"{len(SEED_INCIDENTS)} incidents, "
            f"{len(SEED_INCIDENT_FOLLOWUPS)} incident follow-ups, "
            f"{len(SEED_MEDICATIONS)} medication records, "
            f"{len(SEED_MED_ADMIN_LOG)} med-admin entries, "
            f"{len(SEED_RESTRICTIVE_PRACTICES)} restrictive practices, "
            f"{len(SEED_RISK_ASSESSMENTS)} risk assessments, "
            f"{len(SEED_PREFERENCES)} preferences, "
            f"{len(SEED_DOCUMENTS)} documents, "
            f"{len(seed_users)} users."
        )
        print()
        print("=" * 70)
        print("  Seeded user accounts (dev only — rotate before real data lands)")
        print("=" * 70)
        print(f"  Password for ALL accounts: {SEED_DEV_PASSWORD}")
        print()
        for u in seed_users:
            print(f"    {u.role.value:<18} {u.email}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed())
