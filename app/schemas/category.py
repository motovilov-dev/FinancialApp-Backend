from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from ._base import ORMModel


class CategoryBase(ORMModel):
    title: str = Field(min_length=1, max_length=200)
    monthly_limit: Decimal = Decimal("0")
    order_index: int = 0
    is_hidden: bool = False


class CategoryCreate(CategoryBase):
    id: UUID | None = None
    template_id: UUID | None = None


class CategoryUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    monthly_limit: Decimal | None = None
    order_index: int | None = None
    is_hidden: bool | None = None


class CategoryOut(CategoryBase):
    id: UUID
    group_id: UUID
    template_id: UUID | None = None
