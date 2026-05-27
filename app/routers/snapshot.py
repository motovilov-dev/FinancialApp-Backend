from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_workspace_membership
from ..models.category import Category
from ..models.group import CategoryGroup
from ..models.period import BudgetPeriod
from ..models.transaction import Transaction
from ..schemas.presence import PresenceUser
from ..schemas.sync import WorkspaceSnapshot
from ..services.presence import presence

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["sync"])


@router.get("/snapshot", response_model=WorkspaceSnapshot)
async def snapshot(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    periods = (
        await db.execute(
            select(BudgetPeriod)
            .where(BudgetPeriod.workspace_id == workspace_id)
            .order_by(BudgetPeriod.year, BudgetPeriod.month)
        )
    ).scalars().all()
    period_ids = [p.id for p in periods]

    groups = []
    if period_ids:
        groups = (
            await db.execute(
                select(CategoryGroup)
                .where(CategoryGroup.period_id.in_(period_ids))
                .order_by(CategoryGroup.order_index)
            )
        ).scalars().all()

    group_ids = [g.id for g in groups]
    categories = []
    if group_ids:
        categories = (
            await db.execute(
                select(Category)
                .where(Category.group_id.in_(group_ids))
                .order_by(Category.order_index)
            )
        ).scalars().all()

    category_ids = [c.id for c in categories]
    transactions = []
    if category_ids:
        transactions = (
            await db.execute(
                select(Transaction)
                .where(Transaction.category_id.in_(category_ids))
                .order_by(Transaction.date.desc())
            )
        ).scalars().all()

    return WorkspaceSnapshot(
        workspace_id=workspace_id,
        periods=periods,
        groups=groups,
        categories=categories,
        transactions=transactions,
    )


@router.get("/presence", response_model=list[PresenceUser])
async def get_presence(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
):
    return [PresenceUser(**e.to_dict()) for e in presence.list_for(workspace_id)]
