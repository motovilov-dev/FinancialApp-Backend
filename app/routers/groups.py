from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_workspace_membership
from ..models.group import CategoryGroup
from ..models.period import BudgetPeriod
from ..schemas.group import CategoryGroupCreate, CategoryGroupOut, CategoryGroupUpdate
from ..services.pubsub import broadcast_change
from ._helpers import jsonable

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["groups"])


@router.get("/periods/{period_id}/groups", response_model=list[CategoryGroupOut])
async def list_groups(
    workspace_id: UUID,
    period_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    await _check_period(db, workspace_id, period_id)
    rows = (
        await db.execute(
            select(CategoryGroup).where(CategoryGroup.period_id == period_id).order_by(CategoryGroup.order_index)
        )
    ).scalars().all()
    return rows


@router.post(
    "/periods/{period_id}/groups",
    response_model=CategoryGroupOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    workspace_id: UUID,
    period_id: UUID,
    data: CategoryGroupCreate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    await _check_period(db, workspace_id, period_id)
    group = CategoryGroup(
        id=data.id if data.id else None,  # type: ignore[arg-type]
        period_id=period_id,
        template_id=data.template_id,
        title=data.title.strip(),
        type=data.type,
        accent_hex=data.accent_hex,
        order_index=data.order_index,
        is_hidden=data.is_hidden,
    )
    if data.id is None:
        group.id = None
    db.add(group)
    await db.commit()
    await db.refresh(group)
    out = CategoryGroupOut.model_validate(group)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="group",
        action="created",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.patch("/groups/{group_id}", response_model=CategoryGroupOut)
async def update_group(
    workspace_id: UUID,
    group_id: UUID,
    data: CategoryGroupUpdate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    group = await _get_group(db, workspace_id, group_id)
    for field in ("title", "type", "accent_hex", "order_index", "is_hidden"):
        value = getattr(data, field)
        if value is not None:
            if field == "title":
                value = value.strip()
            setattr(group, field, value)
    await db.commit()
    await db.refresh(group)
    out = CategoryGroupOut.model_validate(group)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="group",
        action="updated",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    workspace_id: UUID,
    group_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    group = await _get_group(db, workspace_id, group_id)
    await db.delete(group)
    await db.commit()
    await broadcast_change(
        workspace_id=workspace_id,
        entity="group",
        action="deleted",
        data={"id": str(group_id)},
        actor_id=member.user_id,
    )


async def _check_period(db: AsyncSession, workspace_id: UUID, period_id: UUID) -> None:
    period = (await db.execute(select(BudgetPeriod).where(BudgetPeriod.id == period_id))).scalar_one_or_none()
    if not period or period.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Период не найден")


async def _get_group(db: AsyncSession, workspace_id: UUID, group_id: UUID) -> CategoryGroup:
    row = (
        await db.execute(
            select(CategoryGroup, BudgetPeriod)
            .join(BudgetPeriod, BudgetPeriod.id == CategoryGroup.period_id)
            .where(CategoryGroup.id == group_id, BudgetPeriod.workspace_id == workspace_id)
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Группа не найдена")
    return row[0]
