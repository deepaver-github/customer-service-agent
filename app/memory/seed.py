"""Seed the database with sample data."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.memory.database import init_db, get_session_factory
from app.memory.models import (
    Account, AccountTier, FAQEntry, Order, OrderStatus,
)


SEED_ORDERS = [
    Order(
        order_id="ORD-1234",
        customer_email="jane@example.com",
        status=OrderStatus.SHIPPED,
        items=[{"name": "Wireless Headphones", "qty": 1, "price": 79.99}],
        tracking_number="1Z999AA10123456784",
        estimated_delivery=date(2026, 5, 28),
    ),
    Order(
        order_id="ORD-5678",
        customer_email="john@example.com",
        status=OrderStatus.PROCESSING,
        items=[
            {"name": "USB-C Cable", "qty": 2, "price": 12.99},
            {"name": "Phone Case", "qty": 1, "price": 24.99},
        ],
        tracking_number=None,
        estimated_delivery=date(2026, 6, 2),
    ),
]

SEED_ACCOUNTS = [
    Account(
        customer_id="CUST-001",
        name="Jane Smith",
        email="jane@example.com",
        tier=AccountTier.GOLD,
        created_at=datetime(2024, 3, 15, tzinfo=timezone.utc),
        total_orders=12,
        open_tickets=0,
    ),
    Account(
        customer_id="CUST-002",
        name="John Doe",
        email="john@example.com",
        tier=AccountTier.STANDARD,
        created_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
        total_orders=3,
        open_tickets=1,
    ),
]

SEED_FAQS = [
    FAQEntry(
        question="What is your return policy?",
        answer="You can return most items within 30 days of delivery for a full refund. Items must be unused and in original packaging. To start a return, contact us with your order number.",
        category="returns",
    ),
    FAQEntry(
        question="How long does shipping take?",
        answer="Standard shipping takes 5-7 business days. Express shipping takes 2-3 business days. Free shipping is available on orders over $50.",
        category="shipping",
    ),
    FAQEntry(
        question="How do I track my order?",
        answer="Once your order ships, you will receive an email with a tracking number. You can also look up your order using your order ID or email address.",
        category="shipping",
    ),
    FAQEntry(
        question="How do I reset my password?",
        answer="Click 'Forgot Password' on the login page and enter your email address. You will receive a password reset link within a few minutes.",
        category="account",
    ),
    FAQEntry(
        question="Do you offer international shipping?",
        answer="Yes, we ship to over 50 countries. International shipping typically takes 10-15 business days. Additional customs fees may apply.",
        category="shipping",
    ),
    FAQEntry(
        question="How do I cancel an order?",
        answer="You can cancel an order within 1 hour of placing it. After that, the order enters processing and cannot be cancelled. You can return it once delivered.",
        category="orders",
    ),
]


async def seed():
    settings = get_settings()
    await init_db(settings.database_url)

    async with get_session_factory()() as db:
        existing = await db.execute(select(Order).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Database already seeded — skipping.")
            return

        for order in SEED_ORDERS:
            db.add(order)
        for account in SEED_ACCOUNTS:
            db.add(account)
        for faq in SEED_FAQS:
            db.add(faq)

        await db.commit()
        print("Seeded: 2 orders, 2 accounts, 6 FAQ entries.")


if __name__ == "__main__":
    asyncio.run(seed())
