from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="get_active_plan",
    description=(
        "Get the participant's current active NDIS plan — plan number, dates, "
        "management type (self / plan-managed / agency-managed), and plan-manager "
        "contact details. Also returns the active service agreements SCA has in "
        "place with that participant."
    ),
)
async def get_active_plan(db: AsyncSession, participant_id: str) -> dict:
    participant = await repo.get_participant(db, participant_id)
    if participant is None:
        return {"error": f"No participant found with id {participant_id}"}

    plan = await repo.get_active_plan_for_participant(db, participant_id)
    if plan is None:
        return {
            "participant_id": participant_id,
            "active_plan": None,
            "message": "No active NDIS plan on file for this participant.",
        }

    agreements = await repo.get_active_service_agreements_for_participant(
        db, participant_id
    )

    return {
        "participant_id": participant_id,
        "active_plan": {
            "plan_number": plan.plan_number,
            "start_date": str(plan.start_date),
            "end_date": str(plan.end_date),
            "management_type": plan.management_type.value,
            "plan_manager_name": plan.plan_manager_name,
            "plan_manager_contact": plan.plan_manager_contact,
            "status": plan.status.value,
        },
        "active_service_agreements": [
            {
                "service": st.name,
                "service_code": st.code,
                "valid_from": str(agreement.valid_from),
                "valid_to": str(agreement.valid_to) if agreement.valid_to else None,
                "scope_notes": agreement.scope_notes,
            }
            for agreement, st in agreements
        ],
    }
