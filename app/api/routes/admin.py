from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    DashboardStats,
    KnowledgeListItem,
    StaffListItem,
)
from app.auth.dependencies import current_staff
from app.memory import repository as repo
from app.memory.database import get_db
from app.memory.models import User

router = APIRouter()


@router.get("/staff", response_model=list[StaffListItem])
async def list_staff(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_staff),
):
    rows = await repo.list_staff(db)
    return [
        StaffListItem(
            id=s.id,
            first_name=s.first_name,
            last_name=s.last_name,
            role=s.role.value,
            status=s.status.value,
            email=s.email,
        )
        for s in rows
    ]


@router.get("/knowledge", response_model=list[KnowledgeListItem])
async def list_knowledge(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_staff),
):
    rows = await repo.list_knowledge_articles(db)
    return [
        KnowledgeListItem(
            id=a.id,
            title=a.title,
            category=a.category.value,
            status=a.status.value,
        )
        for a in rows
    ]


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_staff),
):
    counts = await repo.dashboard_counts(db)
    return DashboardStats(**counts)
