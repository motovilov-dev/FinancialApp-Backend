from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket

log = logging.getLogger(__name__)


class PubSubManager:
    """In-memory pub/sub по workspace.

    На MVP хватит. Когда понадобится горизонтальное масштабирование — заменим
    на Redis pub/sub (тот же интерфейс) без переписывания вызывающего кода.
    """

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def add(self, workspace_id: UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[workspace_id].add(ws)

    async def remove(self, workspace_id: UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[workspace_id].discard(ws)
            if not self._connections[workspace_id]:
                self._connections.pop(workspace_id, None)

    async def broadcast(self, workspace_id: UUID, message: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections.get(workspace_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception as e:  # noqa: BLE001
                log.warning("ws send failed: %s", e)


pubsub = PubSubManager()


async def broadcast_change(
    *,
    workspace_id: UUID,
    entity: str,
    action: str,
    data: Any,
    actor_id: UUID | None,
) -> None:
    """Удобный хелпер: оповестить о CRUD‑событии."""
    await pubsub.broadcast(
        workspace_id,
        {
            "type": "event",
            "entity": entity,
            "action": action,
            "actor_id": str(actor_id) if actor_id else None,
            "data": data,
        },
    )
