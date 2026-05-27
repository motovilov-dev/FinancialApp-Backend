from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_workspace_membership
from ..models.category import Category
from ..models.group import CategoryGroup
from ..models.period import BudgetPeriod
from ..schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from ..services.pubsub import broadcast_change
from ._helpers import jsonable

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["categories"])


@router.get("/groups/{group_id}/categories", response_model=list[CategoryOut])
async def list_categories(
    workspace_id: UUID,
    group_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    await _check_group(db, workspace_id, group_id)
    rows = (
        await db.execute(
            select(Category).where(Category.group_id == group_id).order_by(Category.order_index)
        )
    ).scalars().all()
    return rows


@router.post(
    "/groups/{group_id}/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    workspace_id: UUID,
    group_id: UUID,
    data: CategoryCreate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    await _check_group(db, workspace_id, group_id)
    cat = Category(
        id=data.id if data.id else None,  # type: ignore[arg-type]
        group_id=group_id,
        template_id=data.template_id,
        title=data.title.strip(),
        monthly_limit=data.monthly_limit,
        order_index=data.order_index,
        is_hidden=data.is_hidden,
    )
    if data.id is None:
        cat.id = None
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    out = CategoryOut.model_validate(cat)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="category",
        action="created",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    workspace_id: UUID,
    category_id: UUID,
    data: CategoryUpdate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    cat = await _get_category(db, workspace_id, category_id)
    for field in ("title", "monthly_limit", "order_index", "is_hidden"):
        value = getattr(data, field)
        if value is not None:
            if field == "title":
                value = value.strip()
            setattr(cat, field, value)
    await db.commit()
    await db.refresh(cat)
    out = CategoryOut.model_validate(cat)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="category",
        action="updated",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    workspace_id: UUID,
    category_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    cat = await _get_category(db, workspace_id, category_id)
    await db.delete(cat)
    await db.commit()
    await broadcast_change(
        workspace_id=workspace_id,
        entity="category",
        action="deleted",
        data={"id": str(category_id)},
        actor_id=member.user_id,
    )


async def _check_group(db: AsyncSession, workspace_id: UUID, group_id: UUID) -> None:
    row = (
        await db.execute(
            select(CategoryGroup, BudgetPeriod)
            .join(BudgetPeriod, BudgetPeriod.id == CategoryGroup.period_id)
            .where(CategoryGroup.id == group_id, BudgetPeriod.workspace_id == workspace_id)
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Группа не найдена")


async def _get_category(db: AsyncSession, workspace_id: UUID, category_id: UUID) -> Category:
    row = (
        await db.execute(
            select(Category, CategoryGroup, BudgetPeriod)
            .join(CategoryGroup, CategoryGroup.id == Category.group_id)
            .join(BudgetPeriod, BudgetPeriod.id == CategoryGroup.period_id)
            .where(Category.id == category_id, BudgetPeriod.workspace_id == workspace_id)
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
    return row[0]
