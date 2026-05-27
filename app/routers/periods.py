from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_workspace_membership
from ..models.period import BudgetPeriod
from ..schemas.period import BudgetPeriodCreate, BudgetPeriodOut, BudgetPeriodUpdate
from ..services.pubsub import broadcast_change
from ._helpers import jsonable

router = APIRouter(prefix="/workspaces/{workspace_id}/periods", tags=["periods"])


@router.get("", response_model=list[BudgetPeriodOut])
async def list_periods(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(BudgetPeriod)
            .where(BudgetPeriod.workspace_id == workspace_id)
            .order_by(BudgetPeriod.year, BudgetPeriod.month)
        )
    ).scalars().all()
    return rows


@router.post("", response_model=BudgetPeriodOut, status_code=status.HTTP_201_CREATED)
async def create_period(
    workspace_id: UUID,
    data: BudgetPeriodCreate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    ws, member = membership
    period = BudgetPeriod(
        id=data.id if data.id else None,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        year=data.year,
        month=data.month,
        start_day=data.start_day,
        end_day=data.end_day,
        is_closed=data.is_closed,
    )
    if data.id is None:
        period.id = None  # дефолт UUID4 в модели
    db.add(period)
    await db.commit()
    await db.refresh(period)
    out = BudgetPeriodOut.model_validate(period)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="period",
        action="created",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.patch("/{period_id}", response_model=BudgetPeriodOut)
async def update_period(
    workspace_id: UUID,
    period_id: UUID,
    data: BudgetPeriodUpdate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    period = await _get(db, workspace_id, period_id)
    if data.start_day is not None:
        period.start_day = data.start_day
    if data.end_day is not None:
        period.end_day = data.end_day
    if data.is_closed is not None:
        period.is_closed = data.is_closed
    await db.commit()
    await db.refresh(period)
    out = BudgetPeriodOut.model_validate(period)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="period",
        action="updated",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.delete("/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_period(
    workspace_id: UUID,
    period_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    period = await _get(db, workspace_id, period_id)
    await db.delete(period)
    await db.commit()
    await broadcast_change(
        workspace_id=workspace_id,
        entity="period",
        action="deleted",
        data={"id": str(period_id)},
        actor_id=member.user_id,
    )


async def _get(db: AsyncSession, workspace_id: UUID, period_id: UUID) -> BudgetPeriod:
    period = (await db.execute(select(BudgetPeriod).where(BudgetPeriod.id == period_id))).scalar_one_or_none()
    if not period or period.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Период не найден")
    return period
