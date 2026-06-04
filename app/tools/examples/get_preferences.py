from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.memory.models import PreferenceCategory
from app.tools.registry import register_tool


@register_tool(
    name="get_preferences",
    description=(
        "Get the participant's recorded preferences — communication style, food, "
        "routine, sensory needs, triggers, likes and dislikes. Critical context "
        "for handover and SIL planning. Optionally filter by category."
    ),
)
async def get_preferences(
    db: AsyncSession,
    participant_id: str,
    category: str | None = None,
) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    cat: PreferenceCategory | None = None
    if category:
        try:
            cat = PreferenceCategory(category)
        except ValueError:
            valid = ", ".join(c.value for c in PreferenceCategory)
            return {"error": f"Unknown category '{category}'. Valid: {valid}"}

    prefs = await repo.get_preferences(db, participant_id, category=cat)
    if not prefs:
        return {
            "participant_id": participant_id,
            "preferences": [],
            "message": "No preferences on file yet.",
        }

    return {
        "participant_id": participant_id,
        "preferences": [
            {
                "category": p.category.value,
                "priority": p.priority.value,
                "detail": p.detail,
            }
            for p in prefs
        ],
    }
