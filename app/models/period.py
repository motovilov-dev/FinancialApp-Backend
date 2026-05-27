from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ._common import TimestampMixin, gen_uuid


class BudgetPeriod(Base, TimestampMixin):
    __tablename__ = "budget_periods"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    start_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    end_day: Mapped[int] = mapped_column(Integer, default=31, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
