from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from ._base import ORMModel


class TransactionBase(ORMModel):
    category_id: UUID
    amount: Decimal
    date: datetime
    note: str = Field(default="", max_length=500)


class TransactionCreate(TransactionBase):
    id: UUID | None = None


class TransactionUpdate(ORMModel):
    category_id: UUID | None = None
    amount: Decimal | None = None
    date: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class TransactionOut(TransactionBase):
    id: UUID
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
