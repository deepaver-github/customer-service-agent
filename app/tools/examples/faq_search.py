from __future__ import annotations

from app.tools.registry import register_tool

FAQ_ENTRIES = [
    {
        "question": "What is your return policy?",
        "answer": "You can return most items within 30 days of delivery for a full refund. Items must be unused and in original packaging. To start a return, contact us with your order number.",
    },
    {
        "question": "How long does shipping take?",
        "answer": "Standard shipping takes 5-7 business days. Express shipping takes 2-3 business days. Free shipping is available on orders over $50.",
    },
    {
        "question": "How do I track my order?",
        "answer": "Once your order ships, you will receive an email with a tracking number. You can also look up your order using your order ID or email address.",
    },
    {
        "question": "How do I reset my password?",
        "answer": "Click 'Forgot Password' on the login page and enter your email address. You will receive a password reset link within a few minutes.",
    },
    {
        "question": "Do you offer international shipping?",
        "answer": "Yes, we ship to over 50 countries. International shipping typically takes 10-15 business days. Additional customs fees may apply.",
    },
    {
        "question": "How do I cancel an order?",
        "answer": "You can cancel an order within 1 hour of placing it. After that, the order enters processing and cannot be cancelled. You can return it once delivered.",
    },
]


@register_tool(
    name="search_faq",
    description="Search the FAQ knowledge base for answers to common customer questions. Returns matching FAQ entries.",
)
def search_faq(query: str) -> dict:
    query_lower = query.lower()
    keywords = query_lower.split()

    scored = []
    for entry in FAQ_ENTRIES:
        text = (entry["question"] + " " + entry["answer"]).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [entry for _, entry in scored[:3]]

    if not results:
        return {"results": [], "message": "No matching FAQ entries found"}
    return {"results": results}
