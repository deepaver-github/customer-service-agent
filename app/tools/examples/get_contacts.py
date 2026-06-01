from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_contacts",
    description=(
        "Get the contacts for a participant — family, guardians, support coordinator, "
        "plan manager, GP, advocate, and emergency contact. Returns primary and emergency "
        "contacts first."
    ),
)
async def get_contacts(db: AsyncSession, participant_id: str) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    contacts = await repo.get_contacts_for_participant(db, participant_id)
    if not contacts:
        return {
            "participant_id": participant_id,
            "contacts": [],
            "message": "No contacts on file for this participant.",
        }

    return {
        "participant_id": participant_id,
        "contacts": [
            {
                "name": c.name,
                "relationship": c.relationship_type.value,
                "phone": c.phone,
                "email": c.email,
                "is_primary": c.is_primary,
                "is_emergency": c.is_emergency,
                "notes": c.notes,
            }
            for c in contacts
        ],
    }
