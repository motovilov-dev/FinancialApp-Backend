from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ._base import ORMModel


class PresenceUser(ORMModel):
    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    connected_at: datetime
    connections: int
