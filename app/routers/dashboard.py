from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_workspace_membership
from ..models._common import utcnow
from ..models.dashboard import WorkspaceDashboardSettings
from ..models.user import User
from ..schemas.dashboard import (
    DashboardBackgroundOut,
    DashboardLockInfo,
    DashboardLockResult,
    DashboardSettingsOut,
    DashboardSettingsUpdate,
)
from ..services.pubsub import broadcast_change

router = APIRouter(prefix="/workspaces/{workspace_id}/dashboard", tags=["dashboard"])
settings = get_settings()

LOCK_TTL = timedelta(seconds=60)
BACKGROUNDS_DIR = Path("var/uploads/dashboard-backgrounds")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_EXT_BY_TYPE = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAX_BACKGROUND_BYTES = 15 * 1024 * 1024  # 15 MiB


def _now() -> datetime:
    return utcnow()


def _utc_aware(dt: datetime | None) -> datetime | None:
    """SQLite часто отдаёт naive datetime — приводим к UTC для сравнения с _now()."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _lock_is_active(row: WorkspaceDashboardSettings) -> bool:
    if not row.locked_by_user_id or not row.lock_expires_at:
        return False
    expires = _utc_aware(row.lock_expires_at)
    return expires is not None and expires > _now()


async def _get_or_create(db: AsyncSession, workspace_id: UUID) -> WorkspaceDashboardSettings:
    row = (await db.execute(
        select(WorkspaceDashboardSettings).where(WorkspaceDashboardSettings.workspace_id == workspace_id)
    )).scalar_one_or_none()
    if row is None:
        row = WorkspaceDashboardSettings(workspace_id=workspace_id, layouts_json="{}", appearance_json="{}", version=0)
        db.add(row)
        await db.flush()
    return row


async def _lock_info(db: AsyncSession, row: WorkspaceDashboardSettings) -> DashboardLockInfo:
    if _lock_is_active(row):
        owner = (await db.execute(select(User).where(User.id == row.locked_by_user_id))).scalar_one_or_none()
        return DashboardLockInfo(
            locked_by_user_id=row.locked_by_user_id,
            locked_by_name=(owner.display_name if owner else None) or (owner.email if owner else None),
            locked_by_avatar_url=owner.avatar_url if owner else None,
            expires_at=_utc_aware(row.lock_expires_at),
        )
    return DashboardLockInfo()


def _to_out(row: WorkspaceDashboardSettings, lock: DashboardLockInfo) -> DashboardSettingsOut:
    return DashboardSettingsOut(
        workspace_id=row.workspace_id,
        version=row.version,
        layouts=json.loads(row.layouts_json or "{}"),
        appearance=json.loads(row.appearance_json or "{}"),
        lock=lock,
    )


@router.post("/backgrounds", response_model=DashboardBackgroundOut)
async def upload_dashboard_background(
    workspace_id: UUID,
    file: UploadFile = File(...),
    membership=Depends(get_workspace_membership),
):
    """Загрузить фоновое изображение дашборда workspace (общее для всех участников)."""
    _ = membership
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Только PNG/JPEG/WebP/GIF")
    content = await file.read()
    if len(content) > MAX_BACKGROUND_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Файл больше 15 МБ")

    image_id = uuid4()
    ext = _EXT_BY_TYPE[file.content_type]
    ws_dir = BACKGROUNDS_DIR / str(workspace_id)
    ws_dir.mkdir(parents=True, exist_ok=True)
    path = ws_dir / f"{image_id}.{ext}"
    path.write_bytes(content)

    rel = f"dashboard-backgrounds/{workspace_id}/{image_id}.{ext}"
    url = f"{settings.public_base_url}/static/{rel}?v={int(time.time())}"
    return DashboardBackgroundOut(url=url)


@router.get("", response_model=DashboardSettingsOut)
async def get_settings(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create(db, workspace_id)
    await db.commit()
    lock = await _lock_info(db, row)
    return _to_out(row, lock)


@router.put("", response_model=DashboardSettingsOut)
async def put_settings(
    workspace_id: UUID,
    data: DashboardSettingsUpdate,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    row = await _get_or_create(db, workspace_id)

    # Если кто-то другой держит активный lock — не даём писать.
    if row.locked_by_user_id and row.locked_by_user_id != member.user_id and _lock_is_active(row):
        raise HTTPException(status.HTTP_423_LOCKED, "Дашборд сейчас редактирует другой участник")

    # Optimistic concurrency.
    if data.expected_version != row.version:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Версия устарела: server={row.version}")

    if data.layouts is not None:
        row.layouts_json = json.dumps(data.layouts, ensure_ascii=False)
    if data.appearance is not None:
        row.appearance_json = json.dumps(data.appearance, ensure_ascii=False)
    row.version += 1
    await db.commit()

    lock = await _lock_info(db, row)
    out = _to_out(row, lock)
    await broadcast_change(
        workspace_id=workspace_id,
        entity="dashboard_settings",
        action="updated",
        data=out.model_dump(mode="json"),
        actor_id=member.user_id,
    )
    return out


@router.post("/lock", response_model=DashboardLockResult)
async def acquire_lock(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    """Acquire или продлить lock. Возвращает 423, если активен у другого."""
    _, member = membership
    row = await _get_or_create(db, workspace_id)
    now = _now()
    active_other = row.locked_by_user_id and row.locked_by_user_id != member.user_id and _lock_is_active(row)
    if active_other:
        lock = await _lock_info(db, row)
        raise HTTPException(status.HTTP_423_LOCKED, detail=lock.model_dump(mode="json"))

    row.locked_by_user_id = member.user_id
    row.lock_expires_at = now + LOCK_TTL
    await db.commit()
    lock = await _lock_info(db, row)
    await broadcast_change(
        workspace_id=workspace_id, entity="dashboard_lock", action="updated",
        data=lock.model_dump(mode="json"), actor_id=member.user_id,
    )
    return DashboardLockResult(ok=True, lock=lock)


@router.post("/unlock", response_model=DashboardLockResult)
async def release_lock(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    _, member = membership
    row = await _get_or_create(db, workspace_id)
    # Снимать может только владелец lock'а или если lock уже просрочен.
    if row.locked_by_user_id and row.locked_by_user_id != member.user_id:
        if _lock_is_active(row):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Lock держит другой участник")
    row.locked_by_user_id = None
    row.lock_expires_at = None
    await db.commit()
    lock = DashboardLockInfo()
    await broadcast_change(
        workspace_id=workspace_id, entity="dashboard_lock", action="updated",
        data=lock.model_dump(mode="json"), actor_id=member.user_id,
    )
    return DashboardLockResult(ok=True, lock=lock)


# Внутренний хелпер: освободить lock пользователя при WS-disconnect.
async def release_lock_if_owned(db: AsyncSession, workspace_id: UUID, user_id: UUID) -> bool:
    row = (await db.execute(
        select(WorkspaceDashboardSettings).where(WorkspaceDashboardSettings.workspace_id == workspace_id)
    )).scalar_one_or_none()
    if not row or row.locked_by_user_id != user_id:
        return False
    row.locked_by_user_id = None
    row.lock_expires_at = None
    await db.commit()
    return True
