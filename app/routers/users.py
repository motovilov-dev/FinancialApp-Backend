from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()

AVATARS_DIR = Path("var/uploads/avatars")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_EXT_BY_TYPE = {
    "image/png": "png", "image/jpeg": "jpg",
    "image/webp": "webp", "image/gif": "gif",
}
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MiB


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if data.display_name is not None:
        user.display_name = data.display_name.strip()
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Только PNG/JPEG/WebP/GIF")
    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Файл больше 5 МБ")

    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    ext = _EXT_BY_TYPE[file.content_type]
    # Чистим старый файл с любым расширением
    for old in AVATARS_DIR.glob(f"{user.id}.*"):
        try: old.unlink()
        except OSError: pass

    path = AVATARS_DIR / f"{user.id}.{ext}"
    path.write_bytes(content)

    # Cache-buster, чтобы клиенты сразу подхватили новый файл.
    import time
    user.avatar_url = f"{settings.public_base_url}/static/avatars/{user.id}.{ext}?v={int(time.time())}"
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/me/avatar", response_model=UserOut)
async def delete_avatar(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for old in AVATARS_DIR.glob(f"{user.id}.*"):
        try: old.unlink()
        except OSError: pass
    user.avatar_url = None
    await db.commit()
    await db.refresh(user)
    return user
