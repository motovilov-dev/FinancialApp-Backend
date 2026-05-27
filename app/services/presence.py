from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket


@dataclass
class PresenceEntry:
    user_id: UUID
    display_name: str
    avatar_url: str | None
    connected_at: datetime
    connections: int = 0

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "connected_at": self.connected_at.isoformat(),
            "connections": self.connections,
        }


class PresenceTracker:
    """Кто сейчас «в» workspace. Считаем по user_id; несколько вкладок одного
    пользователя считаются за одну аватарку (но трекаем число коннектов)."""

    def __init__(self) -> None:
        # workspace_id -> { user_id -> PresenceEntry }
        self._by_ws: dict[UUID, dict[UUID, PresenceEntry]] = defaultdict(dict)
        # WebSocket -> (workspace_id, user_id)
        self._by_ws_sock: dict[WebSocket, tuple[UUID, UUID]] = {}
        self._lock = asyncio.Lock()

    async def join(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        display_name: str,
        avatar_url: str | None,
        ws: WebSocket,
    ) -> list[PresenceEntry]:
        async with self._lock:
            entries = self._by_ws[workspace_id]
            entry = entries.get(user_id)
            if entry is None:
                entry = PresenceEntry(
                    user_id=user_id,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    connected_at=datetime.now(timezone.utc),
                    connections=0,
                )
                entries[user_id] = entry
            entry.connections += 1
            self._by_ws_sock[ws] = (workspace_id, user_id)
            return list(entries.values())

    async def leave(self, ws: WebSocket) -> tuple[UUID, list[PresenceEntry]] | None:
        async with self._lock:
            mapping = self._by_ws_sock.pop(ws, None)
            if not mapping:
                return None
            workspace_id, user_id = mapping
            entries = self._by_ws[workspace_id]
            entry = entries.get(user_id)
            if entry:
                entry.connections -= 1
                if entry.connections <= 0:
                    entries.pop(user_id, None)
            if not entries:
                self._by_ws.pop(workspace_id, None)
            return workspace_id, list(self._by_ws.get(workspace_id, {}).values())

    def list_for(self, workspace_id: UUID) -> list[PresenceEntry]:
        return list(self._by_ws.get(workspace_id, {}).values())


presence = PresenceTracker()
