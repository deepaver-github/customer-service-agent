from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Account, AuditLog
from app.tools.registry import register_tool

SAFE_FIELDS = {"customer_id", "name", "email", "tier", "total_orders", "open_tickets", "created_at"}


def _sanitize(values: dict | None) -> dict | None:
    if values is None:
        return None
    return {k: v for k, v in values.items() if k in SAFE_FIELDS}


@register_tool(
    name="get_account_history",
    description="Get the history of changes to a customer account by customer ID or email. Shows when the account was created and any updates made to it.",
)
async def get_account_history(db: AsyncSession, customer_id: str | None = None, email: str | None = None) -> dict:
    if customer_id:
        stmt = select(Account).where(Account.customer_id == customer_id)
    elif email:
        stmt = select(Account).where(Account.email == email)
    else:
        return {"error": "Please provide a customer_id or email"}

    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if account is None:
        return {"error": "Account not found"}

    audit_stmt = (
        select(AuditLog)
        .where(AuditLog.table_name == "accounts")
        .where(AuditLog.record_id == account.id)
        .order_by(AuditLog.changed_at)
    )
    audit_result = await db.execute(audit_stmt)
    entries = audit_result.scalars().all()

    history = []
    for entry in entries:
        record = {"action": entry.action.value}
        if entry.changed_at:
            record["date"] = entry.changed_at.strftime("%Y-%m-%d %H:%M UTC")
        old = _sanitize(entry.old_values)
        new = _sanitize(entry.new_values)
        if entry.action.value == "UPDATE" and old and new:
            changes = {k: {"from": old.get(k), "to": new[k]} for k in new if old.get(k) != new[k]}
            if changes:
                record["changes"] = changes
        history.append(record)

    return {
        "customer_id": account.customer_id,
        "name": account.name,
        "account_created": account.created_at.strftime("%Y-%m-%d"),
        "history": history,
    }
