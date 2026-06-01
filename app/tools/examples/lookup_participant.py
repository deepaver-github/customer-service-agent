from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


def _participant_dict(p) -> dict:
    return {
        "id": p.id,
        "ndis_number": p.ndis_number,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "preferred_name": p.preferred_name,
        "primary_disability_category": (
            p.primary_disability_category.value
            if p.primary_disability_category is not None
            else None
        ),
        "status": p.status.value,
        "communication_needs": p.communication_needs,
        "suburb": p.suburb,
        "state": p.state.value if p.state is not None else None,
    }


@register_tool(
    name="lookup_participant",
    description=(
        "Find a Special Care Australia participant by NDIS number, name, or email. "
        "Returns the participant's record including communication needs and current status. "
        "If multiple participants match a name search, returns up to 5 results."
    ),
)
async def lookup_participant(
    db: AsyncSession,
    ndis_number: str | None = None,
    name_or_email: str | None = None,
) -> dict:
    if ndis_number:
        participant = await repo.get_participant_by_ndis_number(db, ndis_number)
        if participant is None:
            return {"error": f"No participant found with NDIS number {ndis_number}"}
        return {"match": "single", "participant": _participant_dict(participant)}

    if name_or_email:
        matches = await repo.search_participants_by_name(db, name_or_email)
        if not matches:
            return {"error": f"No participants found matching '{name_or_email}'"}
        if len(matches) == 1:
            return {"match": "single", "participant": _participant_dict(matches[0])}
        return {
            "match": "multiple",
            "participants": [_participant_dict(p) for p in matches],
        }

    return {"error": "Please provide an ndis_number or name_or_email to search"}
