from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_goals",
    description=(
        "Get the participant's NDIS goals. Returns active goals by default; pass "
        "include_inactive=true to also include achieved, paused, or removed goals."
    ),
)
async def get_goals(
    db: AsyncSession,
    participant_id: str,
    include_inactive: bool = False,
) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    goals = await repo.get_goals_for_participant(
        db, participant_id, include_inactive=include_inactive
    )
    if not goals:
        return {
            "participant_id": participant_id,
            "goals": [],
            "message": "No goals on file for this participant.",
        }

    return {
        "participant_id": participant_id,
        "goals": [
            {
                "description": g.description,
                "category": g.category.value,
                "target_date": str(g.target_date) if g.target_date else None,
                "status": g.status.value,
            }
            for g in goals
        ],
    }
