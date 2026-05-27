from __future__ import annotations

from uuid import UUID

from pydantic import Field

from ._base import ORMModel


class BudgetPeriodBase(ORMModel):
    year: int = Field(ge=2000, le=3000)
    month: int = Field(ge=1, le=12)
    start_day: int = Field(default=1, ge=1, le=28)
    end_day: int = Field(default=31, ge=1, le=31)
    is_closed: bool = False


class BudgetPeriodCreate(BudgetPeriodBase):
    id: UUID | None = None


class BudgetPeriodUpdate(ORMModel):
    start_day: int | None = Field(default=None, ge=1, le=28)
    end_day: int | None = Field(default=None, ge=1, le=31)
    is_closed: bool | None = None


class BudgetPeriodOut(BudgetPeriodBase):
    id: UUID
    workspace_id: UUID
