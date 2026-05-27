from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from ._base import ORMModel


class DashboardLockInfo(ORMModel):
    locked_by_user_id: UUID | None = None
    locked_by_name: str | None = None
    locked_by_avatar_url: str | None = None
    expires_at: datetime | None = None


class DashboardSettingsOut(ORMModel):
    workspace_id: UUID
    version: int
    layouts: dict[str, Any] = Field(default_factory=dict)
    appearance: dict[str, Any] = Field(default_factory=dict)
    lock: DashboardLockInfo = DashboardLockInfo()


class DashboardSettingsUpdate(ORMModel):
    # Если version отличается — 409.
    expected_version: int
    layouts: dict[str, Any] | None = None
    appearance: dict[str, Any] | None = None


class DashboardLockResult(ORMModel):
    ok: bool
    lock: DashboardLockInfo


class DashboardBackgroundOut(ORMModel):
    """Публичный URL загруженного фона дашборда (в appearance.customBackgroundPaths)."""

    url: str
