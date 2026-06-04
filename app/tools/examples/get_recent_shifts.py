from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_recent_shifts",
    description=(
        "Get the participant's most recent shifts that have already happened "
        "(default 5) — completed, cancelled, or no-show. Useful for handover "
        "context."
    ),
)
async def get_recent_shifts(
    db: AsyncSession,
    participant_id: str,
    limit: int = 5,
) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    rows = await repo.get_recent_shifts(db, participant_id, limit=limit)
    if not rows:
        return {
            "participant_id": participant_id,
            "recent_shifts": [],
            "message": "No past shifts on record for this participant.",
        }

    return {
        "participant_id": participant_id,
        "recent_shifts": [
            {
                "service": st.name,
                "service_code": st.code,
                "scheduled_start": shift.scheduled_start.isoformat(),
                "scheduled_end": shift.scheduled_end.isoformat(),
                "actual_start": (
                    shift.actual_start.isoformat() if shift.actual_start else None
                ),
                "actual_end": (
                    shift.actual_end.isoformat() if shift.actual_end else None
                ),
                "location": shift.location,
                "support_worker": (
                    f"{staff.first_name} {staff.last_name}"
                    if staff is not None else "Unassigned"
                ),
                "status": shift.status.value,
                "cancelled_reason": shift.cancelled_reason,
            }
            for shift, st, staff in rows
        ],
    }
