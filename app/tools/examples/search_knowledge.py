from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory import repository as repo
from app.tools.registry import register_tool


@register_tool(
    name="search_knowledge",
    description=(
        "Search the Special Care Australia knowledge base for answers about services, "
        "the NDIS, how to start receiving supports, plan management, complaints and feedback. "
        "Returns up to 5 matching published articles."
    ),
)
async def search_knowledge(db: AsyncSession, query: str) -> dict:
    articles = await repo.search_knowledge_articles(db, query)
    if not articles:
        return {"results": [], "message": "No matching articles found."}

    return {
        "results": [
            {
                "title": a.title,
                "category": a.category.value,
                "body": a.body_md,
            }
            for a in articles
        ]
    }
