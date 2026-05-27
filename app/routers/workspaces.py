from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import (
    get_current_user,
    get_workspace_membership,
    require_owner_or_admin,
)
from ..models.user import User
from ..models.workspace import MemberRole, Workspace, WorkspaceMember
from ..schemas.workspace import (
    InviteCodeOut,
    JoinByCodeIn,
    MemberInvite,
    MemberOut,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from ..models.workspace import _gen_invite_code

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Workspace).join(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        )
    ).scalars().all()
    return rows


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = Workspace(name=data.name.strip(), kind=data.kind, owner_id=user.id)
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=MemberRole.owner))
    await db.commit()
    await db.refresh(ws)
    return ws


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    membership=Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ws, _ = membership
    if data.name is not None:
        ws.name = data.name.strip()
    if data.kind is not None:
        ws.kind = data.kind
    await db.commit()
    await db.refresh(ws)
    return ws


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    membership=Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ws, member = membership
    if member.role != MemberRole.owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Удалять может только владелец")
    await db.delete(ws)
    await db.commit()


# --- Invite by code -------------------------------------------------------


@router.post("/join", response_model=WorkspaceOut)
async def join_by_code(
    data: JoinByCodeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = data.code.strip().upper()
    ws = (await db.execute(select(Workspace).where(Workspace.invite_code == code))).scalar_one_or_none()
    if not ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Код не найден")

    exists = (
        await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if exists:
        return ws

    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=MemberRole.member))
    await db.commit()
    await db.refresh(ws)
    return ws


@router.get("/{workspace_id}/invite-code", response_model=InviteCodeOut)
async def get_invite_code(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
):
    ws, _ = membership
    return InviteCodeOut(invite_code=ws.invite_code)


@router.post("/{workspace_id}/invite-code/regenerate", response_model=InviteCodeOut)
async def regenerate_invite_code(
    workspace_id: UUID,
    membership=Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ws, _ = membership
    # На случай коллизий — пара попыток.
    for _ in range(5):
        candidate = _gen_invite_code()
        clash = (await db.execute(select(Workspace).where(Workspace.invite_code == candidate))).scalar_one_or_none()
        if not clash:
            ws.invite_code = candidate
            await db.commit()
            return InviteCodeOut(invite_code=candidate)
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Не удалось сгенерировать код")


# --- Members --------------------------------------------------------------


@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(
    workspace_id: UUID,
    membership=Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).all()
    return [
        MemberOut(
            id=m.id,
            user_id=u.id,
            role=m.role,
            display_name=u.display_name or u.email,
            email=u.email,
            avatar_url=u.avatar_url,
        )
        for (m, u) in rows
    ]


@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: UUID,
    data: MemberInvite,
    membership=Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """MVP‑инвайт: добавляет уже зарегистрированного пользователя по email.

    После подключения email‑инвайтов сюда добавим отправку письма со ссылкой
    на регистрацию/вступление.
    """
    invitee = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if not invitee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь с таким email не зарегистрирован")
    exists = (
        await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == invitee.id,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Уже участник")
    m = WorkspaceMember(workspace_id=workspace_id, user_id=invitee.id, role=data.role)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return MemberOut(
        id=m.id,
        user_id=invitee.id,
        role=m.role,
        display_name=invitee.display_name or invitee.email,
        email=invitee.email,
        avatar_url=invitee.avatar_url,
    )


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: UUID,
    member_id: UUID,
    membership=Depends(require_owner_or_admin),
    db: AsyncSession = Depends(get_db),
):
    m = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.id == member_id))).scalar_one_or_none()
    if not m or m.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Участник не найден")
    if m.role == MemberRole.owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нельзя удалить владельца")
    await db.delete(m)
    await db.commit()
