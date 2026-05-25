from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Order
from app.tools.registry import register_tool


@register_tool(
    name="lookup_order",
    description="Look up an order by order ID or customer email address. Returns order details including status, items, and tracking information.",
)
async def lookup_order(db: AsyncSession, order_id: str | None = None, email: str | None = None) -> dict:
    if order_id:
        stmt = select(Order).where(Order.order_id == order_id)
    elif email:
        stmt = select(Order).where(Order.customer_email == email)
    else:
        return {"error": "Please provide an order_id or email"}

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        return {"error": "Order not found"}

    return {
        "order_id": order.order_id,
        "customer_email": order.customer_email,
        "status": order.status.value,
        "items": order.items,
        "tracking_number": order.tracking_number,
        "estimated_delivery": str(order.estimated_delivery) if order.estimated_delivery else None,
    }
