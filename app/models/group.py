from __future__ import annotations

import enum
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ._common import TimestampMixin, gen_uuid


class CategoryGroupType(str, enum.Enum):
    expense = "expense"
    income = "income"
    debt = "debt"
    savings = "savings"


class CategoryGroup(Base, TimestampMixin):
    __tablename__ = "category_groups"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    period_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("budget_periods.id", ondelete="CASCADE"), index=True, nullable=False
    )
    template_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[CategoryGroupType] = mapped_column(
        Enum(CategoryGroupType, native_enum=False, length=16),
        default=CategoryGroupType.expense,
        nullable=False,
    )
    # Цвет в hex `#RRGGBB`. Опционально.
    accent_hex: Mapped[str | None] = mapped_column(String(9), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
