from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ._common import TimestampMixin


class WorkspaceDashboardSettings(Base, TimestampMixin):
    """Общие настройки дашборда workspace'а: layouts и appearance.
    JSON хранится как text (SQLite/Postgres-agnostic). Версия инкрементится
    каждым PUT — клиент шлёт её при сохранении для optimistic concurrency.
    """
    __tablename__ = "workspace_dashboard_settings"

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    layouts_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    appearance_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Lock: кто сейчас редактирует и до какого времени блокировка валидна.
    locked_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
