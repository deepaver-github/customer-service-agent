from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Account
from app.tools.registry import register_tool


@register_tool(
    name="get_account_info",
    description="Retrieve customer account information by customer ID. Returns account details including tier, order history, and open tickets.",
)
async def get_account_info(db: AsyncSession, customer_id: str) -> dict:
    stmt = select(Account).where(Account.customer_id == customer_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if account is None:
        return {"error": "Account not found"}

    return {
        "customer_id": account.customer_id,
        "name": account.name,
        "email": account.email,
        "tier": account.tier.value,
        "account_created": str(account.created_at.date()),
        "total_orders": account.total_orders,
        "open_tickets": account.open_tickets,
    }
