from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_upcoming_shifts",
    description=(
        "Get the participant's next scheduled shifts (default 5). Returns the "
        "service type, scheduled start and end, location, and assigned support "
        "worker name when one is rostered."
    ),
)
async def get_upcoming_shifts(
    db: AsyncSession,
    participant_id: str,
    limit: int = 5,
) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    rows = await repo.get_upcoming_shifts(db, participant_id, limit=limit)
    if not rows:
        return {
            "participant_id": participant_id,
            "upcoming_shifts": [],
            "message": "No scheduled shifts coming up for this participant.",
        }

    return {
        "participant_id": participant_id,
        "upcoming_shifts": [
            {
                "service": st.name,
                "service_code": st.code,
                "scheduled_start": shift.scheduled_start.isoformat(),
                "scheduled_end": shift.scheduled_end.isoformat(),
                "location": shift.location,
                "support_worker": (
                    f"{staff.first_name} {staff.last_name}"
                    if staff is not None else "Unassigned"
                ),
                "status": shift.status.value,
            }
            for shift, st, staff in rows
        ],
    }
