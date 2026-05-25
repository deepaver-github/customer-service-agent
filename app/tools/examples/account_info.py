from __future__ import annotations

from app.tools.registry import register_tool

MOCK_ACCOUNTS = {
    "CUST-001": {
        "customer_id": "CUST-001",
        "name": "Jane Smith",
        "email": "jane@example.com",
        "tier": "gold",
        "account_created": "2024-03-15",
        "total_orders": 12,
        "open_tickets": 0,
    },
    "CUST-002": {
        "customer_id": "CUST-002",
        "name": "John Doe",
        "email": "john@example.com",
        "tier": "standard",
        "account_created": "2025-01-10",
        "total_orders": 3,
        "open_tickets": 1,
    },
}


@register_tool(
    name="get_account_info",
    description="Retrieve customer account information by customer ID. Returns account details including tier, order history, and open tickets.",
)
def get_account_info(customer_id: str) -> dict:
    if customer_id in MOCK_ACCOUNTS:
        return MOCK_ACCOUNTS[customer_id]
    return {"error": "Account not found", "customer_id": customer_id}
