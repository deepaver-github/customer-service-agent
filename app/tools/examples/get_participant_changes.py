from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_participant_changes",
    description=(
        "Get the most recent audit-log entries for a participant — who or what "
        "changed across plans, goals, contacts, shifts, incidents, medications, "
        "and other tracked records. Returns table_name, action, changed_at."
    ),
)
async def get_participant_changes(
    db: AsyncSession,
    participant_id: str,
    limit: int = 20,
) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    entries = await repo.get_participant_audit_history(
        db, participant_id, limit=limit
    )
    if not entries:
        return {
            "participant_id": participant_id,
            "changes": [],
            "message": "No recent recorded changes for this participant.",
        }

    return {
        "participant_id": participant_id,
        "changes": [
            {
                "table": entry.table_name,
                "record_id": entry.record_id,
                "action": entry.action.value if hasattr(entry.action, "value") else str(entry.action),
                "changed_at": entry.changed_at.isoformat(),
            }
            for entry in entries
        ],
    }
