from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models.user import User
from .models.workspace import MemberRole, Workspace, WorkspaceMember
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Не авторизован")
    try:
        payload = decode_token(token, expected_purpose="access")
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    uid = UUID(payload["sub"])
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return user


async def require_verified(user: User = Depends(get_current_user)) -> User:
    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email не подтверждён")
    return user


async def get_workspace_membership(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Workspace, WorkspaceMember]:
    ws = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one_or_none()
    if not ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace не найден")
    member = (
        await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к workspace")
    return ws, member


async def require_owner_or_admin(
    membership: tuple[Workspace, WorkspaceMember] = Depends(get_workspace_membership),
) -> tuple[Workspace, WorkspaceMember]:
    _, member = membership
    if member.role not in (MemberRole.owner, MemberRole.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    return membership
