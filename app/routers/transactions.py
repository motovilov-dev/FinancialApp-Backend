from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_workspace_membership
from ..models.category import Category
from ..models.group import CategoryGroup
from ..models.period import BudgetPeriod
from ..models.transaction import Transaction
from ..schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate
from ..services.pubsub import broadcast_change
from ._helpers import jsonable

router = APIRouter(prefix="/workspaces/{workspace_id}/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    workspace_id: UUID,
    period_id: UUID | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .join(CategoryGroup, CategoryGroup.id == Category.group_id)
        .join(BudgetPeriod, BudgetPeriod.id == CategoryGroup.period_id)
        .where(BudgetPeriod.workspace_id == workspace_id)
        .order_by(Transaction.date.desc())
        .limit(limit)
    )
    if period_id:
        q = q.where(BudgetPeriod.id == period_id)
    return (await db.execute(q)).scalars().all()


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    workspace_id: UUID,
    data: TransactionCreate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    await _check_category(db, workspace_id, data.category_id)
    tx = Transaction(
        id=data.id if data.id else None,  # type: ignore[arg-type]
        category_id=data.category_id,
        amount=data.amount,
        date=data.date,
        note=data.note,
        created_by_user_id=member.user_id,
    )
    if data.id is None:
        tx.id = None
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    out = TransactionOut.model_validate(tx)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="transaction",
        action="created",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.patch("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    workspace_id: UUID,
    transaction_id: UUID,
    data: TransactionUpdate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    tx = await _get_transaction(db, workspace_id, transaction_id)
    if data.category_id is not None:
        await _check_category(db, workspace_id, data.category_id)
        tx.category_id = data.category_id
    if data.amount is not None:
        tx.amount = data.amount
    if data.date is not None:
        tx.date = data.date
    if data.note is not None:
        tx.note = data.note
    await db.commit()
    await db.refresh(tx)
    out = TransactionOut.model_validate(tx)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="transaction",
        action="updated",
        data=jsonable(out),
        actor_id=member.user_id,
    )
    return out


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    workspace_id: UUID,
    transaction_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    tx = await _get_transaction(db, workspace_id, transaction_id)
    await db.delete(tx)
    await db.commit()
    await broadcast_change(
        workspace_id=workspace_id,
        entity="transaction",
        action="deleted",
        data={"id": str(transaction_id)},
        actor_id=member.user_id,
    )


async def _check_category(db: AsyncSession, workspace_id: UUID, category_id: UUID) -> None:
    row = (
        await db.execute(
            select(Category, CategoryGroup, BudgetPeriod)
            .join(CategoryGroup, CategoryGroup.id == Category.group_id)
            .join(BudgetPeriod, BudgetPeriod.id == CategoryGroup.period_id)
            .where(Category.id == category_id, BudgetPeriod.workspace_id == workspace_id)
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена в этом workspace")


async def _get_transaction(db: AsyncSession, workspace_id: UUID, transaction_id: UUID) -> Transaction:
    row = (
        await db.execute(
            select(Transaction, Category, CategoryGroup, BudgetPeriod)
            .join(Category, Category.id == Transaction.category_id)
            .join(CategoryGroup, CategoryGroup.id == Category.group_id)
            .join(BudgetPeriod, BudgetPeriod.id == CategoryGroup.period_id)
            .where(Transaction.id == transaction_id, BudgetPeriod.workspace_id == workspace_id)
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Транзакция не найдена")
    return row[0]
