from __future__ import annotations

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import FAQEntry
from app.tools.registry import register_tool


@register_tool(
    name="search_faq",
    description="Search the FAQ knowledge base for answers to common customer questions. Returns matching FAQ entries.",
)
async def search_faq(db: AsyncSession, query: str) -> dict:
    keywords = query.lower().split()
    conditions = []
    for kw in keywords:
        pattern = f"%{kw}%"
        conditions.append(FAQEntry.question.ilike(pattern))
        conditions.append(FAQEntry.answer.ilike(pattern))

    stmt = select(FAQEntry).where(or_(*conditions)).limit(5)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        return {"results": [], "message": "No matching FAQ entries found"}

    return {
        "results": [
            {"question": e.question, "answer": e.answer}
            for e in entries
        ]
    }
