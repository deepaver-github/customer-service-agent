from __future__ import annotations

from app.tools.registry import register_tool

MOCK_ORDERS = {
    "ORD-1234": {
        "order_id": "ORD-1234",
        "customer_email": "jane@example.com",
        "status": "shipped",
        "items": [{"name": "Wireless Headphones", "qty": 1, "price": 79.99}],
        "tracking_number": "1Z999AA10123456784",
        "estimated_delivery": "2026-05-28",
    },
    "ORD-5678": {
        "order_id": "ORD-5678",
        "customer_email": "john@example.com",
        "status": "processing",
        "items": [
            {"name": "USB-C Cable", "qty": 2, "price": 12.99},
            {"name": "Phone Case", "qty": 1, "price": 24.99},
        ],
        "tracking_number": None,
        "estimated_delivery": "2026-06-02",
    },
}


@register_tool(
    name="lookup_order",
    description="Look up an order by order ID or customer email address. Returns order details including status, items, and tracking information.",
)
def lookup_order(order_id: str | None = None, email: str | None = None) -> dict:
    if order_id and order_id in MOCK_ORDERS:
        return MOCK_ORDERS[order_id]

    if email:
        for order in MOCK_ORDERS.values():
            if order["customer_email"] == email:
                return order

    return {"error": "Order not found", "searched_by": {"order_id": order_id, "email": email}}
