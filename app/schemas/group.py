from __future__ import annotations

from uuid import UUID

from pydantic import Field

from ..models.group import CategoryGroupType
from ._base import ORMModel


class CategoryGroupBase(ORMModel):
    title: str = Field(min_length=1, max_length=200)
    type: CategoryGroupType = CategoryGroupType.expense
    accent_hex: str | None = Field(default=None, max_length=9)
    order_index: int = 0
    is_hidden: bool = False


class CategoryGroupCreate(CategoryGroupBase):
    id: UUID | None = None
    template_id: UUID | None = None


class CategoryGroupUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    type: CategoryGroupType | None = None
    accent_hex: str | None = None
    order_index: int | None = None
    is_hidden: bool | None = None


class CategoryGroupOut(CategoryGroupBase):
    id: UUID
    period_id: UUID
    template_id: UUID | None = None
