from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_medications",
    description=(
        "Get the participant's active medication records — name, dose, route, "
        "frequency, prescriber, PRN flag, and notes. Does NOT include the "
        "administration log; this is the current prescription list."
    ),
)
async def get_medications(db: AsyncSession, participant_id: str) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    meds = await repo.get_active_medications(db, participant_id)
    if not meds:
        return {
            "participant_id": participant_id,
            "medications": [],
            "message": "No active medication records on file.",
        }

    return {
        "participant_id": participant_id,
        "medications": [
            {
                "name": m.medication_name,
                "dose": m.dose,
                "route": m.route.value,
                "frequency": m.frequency,
                "prn": m.prn,
                "prescriber": m.prescriber,
                "start_date": str(m.start_date),
                "end_date": str(m.end_date) if m.end_date else None,
                "notes": m.notes,
            }
            for m in meds
        ],
    }
