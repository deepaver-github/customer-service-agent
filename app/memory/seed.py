"""Seed the database with Special Care Australia sample data."""
from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select

from app.config import get_settings
from app.memory.database import init_db, get_session_factory
from app.memory.models import (
    AssignmentType,
    AustralianState,
    Contact,
    ContactRelationship,
    DisabilityCategory,
    KnowledgeArticle,
    KnowledgeCategory,
    KnowledgeStatus,
    NDISCategory,
    Participant,
    ParticipantStaffAssignment,
    ParticipantStatus,
    ServiceType,
    ServiceTypeStatus,
    Staff,
    StaffRole,
    StaffStatus,
)


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


async def seed() -> None:
    settings = get_settings()
    await init_db(settings.database_url)

    async with get_session_factory()() as db:
        existing = await db.execute(select(Participant).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Database already seeded — skipping.")
            return

        # Parents first (participants + staff), then children that reference them.
        # An explicit flush between batches forces FK-safe insert ordering on Postgres.
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

        await db.commit()
        print(
            f"Seeded: {len(SEED_PARTICIPANTS)} participants, "
            f"{len(SEED_STAFF)} staff, "
            f"{len(SEED_CONTACTS)} contacts, "
            f"{len(SEED_ASSIGNMENTS)} assignments, "
            f"{len(SEED_SERVICE_TYPES)} service types, "
            f"{len(SEED_KNOWLEDGE)} knowledge articles."
        )


if __name__ == "__main__":
    asyncio.run(seed())
