from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import AuditLog, Order
from app.tools.registry import register_tool

SAFE_FIELDS = {"order_id", "customer_email", "status", "items", "tracking_number", "estimated_delivery", "created_at"}


def _sanitize(values: dict | None) -> dict | None:
    if values is None:
        return None
    return {k: v for k, v in values.items() if k in SAFE_FIELDS}


STATUS_LABELS = {
    "PENDING": "Order placed",
    "PROCESSING": "Order is being processed",
    "SHIPPED": "Order dispatched",
    "DELIVERED": "Order delivered",
    "CANCELLED": "Order cancelled",
}


@register_tool(
    name="get_order_history",
    description="Get the full history and timeline of an order by order ID or customer email. Shows when the order was created, status changes (processed, dispatched, delivered), and tracking updates.",
)
async def get_order_history(db: AsyncSession, order_id: str | None = None, email: str | None = None) -> dict:
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

    audit_stmt = (
        select(AuditLog)
        .where(AuditLog.table_name == "orders")
        .where(AuditLog.record_id == order.id)
        .order_by(AuditLog.changed_at)
    )
    audit_result = await db.execute(audit_stmt)
    entries = audit_result.scalars().all()

    timeline = []
    for entry in entries:
        date_str = entry.changed_at.strftime("%Y-%m-%d %H:%M UTC") if entry.changed_at else None

        if entry.action.value == "INSERT":
            new = _sanitize(entry.new_values) or {}
            status = new.get("status", "PENDING")
            timeline.append({
                "event": STATUS_LABELS.get(status, "Order created"),
                "date": date_str,
                "status": status.lower(),
            })
        elif entry.action.value == "UPDATE":
            old = _sanitize(entry.old_values) or {}
            new = _sanitize(entry.new_values) or {}
            old_status = old.get("status")
            new_status = new.get("status")
            if new_status and new_status != old_status:
                event = {
                    "event": STATUS_LABELS.get(new_status, f"Status changed to {new_status}"),
                    "date": date_str,
                    "status": new_status.lower(),
                }
                if new_status == "SHIPPED" and new.get("tracking_number"):
                    event["tracking_number"] = new["tracking_number"]
                if new.get("estimated_delivery"):
                    event["estimated_delivery"] = new["estimated_delivery"]
                timeline.append(event)
            else:
                changes = {k: new[k] for k in new if old.get(k) != new.get(k)}
                if changes:
                    timeline.append({
                        "event": "Order updated",
                        "date": date_str,
                        "details": changes,
                    })

    return {
        "order_id": order.order_id,
        "current_status": order.status.value.lower(),
        "items": order.items,
        "tracking_number": order.tracking_number,
        "estimated_delivery": str(order.estimated_delivery) if order.estimated_delivery else None,
        "timeline": timeline,
    }
