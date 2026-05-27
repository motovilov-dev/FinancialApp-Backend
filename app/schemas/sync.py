from __future__ import annotations

from uuid import UUID

from ._base import ORMModel
from .category import CategoryOut
from .group import CategoryGroupOut
from .period import BudgetPeriodOut
from .transaction import TransactionOut


class WorkspaceSnapshot(ORMModel):
    """Полный bootstrap клиента: всё, что нужно отрисовать сразу."""

    workspace_id: UUID
    version: int = 1
    periods: list[BudgetPeriodOut]
    groups: list[CategoryGroupOut]
    categories: list[CategoryOut]
    transactions: list[TransactionOut]
