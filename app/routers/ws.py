from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from ..database import SessionLocal
from ..models.user import User
from ..models.workspace import WorkspaceMember
from ..security import decode_token
from ..services.presence import presence
from ..services.pubsub import pubsub

router = APIRouter(tags=["ws"])
log = logging.getLogger(__name__)


@router.websocket("/ws/workspaces/{workspace_id}")
async def workspace_ws(
    websocket: WebSocket,
    workspace_id: UUID,
    token: str = Query(...),
):
    """Realtime канал workspace'а.

    Подключение: `ws://host/ws/workspaces/<wid>?token=<access_jwt>`

    Сразу после auth:
      1. отправляем hello
      2. отправляем presence snapshot
      3. broadcast'им новое presence всем (включая нас)

    Дальше сервер шлёт `event`‑сообщения по мере мутаций (см. PubSubManager).
    Клиент может слать `{"type":"ping"}` — ответим `{"type":"pong"}`.
    """
    # 1. Валидация токена + членства до accept'а — отбиваем чужих сразу.
    try:
        payload = decode_token(token, expected_purpose="access")
        user_id = UUID(payload["sub"])
    except Exception as e:  # noqa: BLE001
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"auth: {e}")
        return

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="user not found")
            return
        member = (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if not member:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="not a member")
            return

    await websocket.accept()

    # 2. Регистрируем connection + presence
    await pubsub.add(workspace_id, websocket)
    entries = await presence.join(
        workspace_id=workspace_id,
        user_id=user.id,
        display_name=user.display_name or user.email,
        avatar_url=user.avatar_url,
        ws=websocket,
    )

    try:
        await websocket.send_json({
            "type": "hello",
            "user_id": str(user.id),
            "workspace_id": str(workspace_id),
        })
        await pubsub.broadcast(workspace_id, {
            "type": "presence",
            "users": [e.to_dict() for e in entries],
        })

        # 3. Цикл: ловим ping/pong и реагируем; других сообщений от клиента
        #    в MVP не ждём (мутации — через HTTP).
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        log.warning("ws loop error: %s", e)
    finally:
        await pubsub.remove(workspace_id, websocket)
        result = await presence.leave(websocket)
        if result is not None:
            wid, entries = result
            await pubsub.broadcast(wid, {
                "type": "presence",
                "users": [e.to_dict() for e in entries],
            })
        # Если уходящий пользователь держал lock — отпускаем и оповещаем.
        from .dashboard import release_lock_if_owned
        from ..schemas.dashboard import DashboardLockInfo
        async with SessionLocal() as db:
            released = await release_lock_if_owned(db, workspace_id, user.id)
        if released:
            await pubsub.broadcast(workspace_id, {
                "type": "event",
                "entity": "dashboard_lock",
                "action": "updated",
                "actor_id": None,
                "data": DashboardLockInfo().model_dump(mode="json"),
            })
