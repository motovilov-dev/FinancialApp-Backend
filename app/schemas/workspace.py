from __future__ import annotations

from uuid import UUID

from pydantic import EmailStr, Field

from ..models.workspace import MemberRole, WorkspaceKind
from ._base import ORMModel


class WorkspaceCreate(ORMModel):
    name: str = Field(min_length=1, max_length=120)
    kind: WorkspaceKind = WorkspaceKind.personal


class WorkspaceUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: WorkspaceKind | None = None


class WorkspaceOut(ORMModel):
    id: UUID
    name: str
    kind: WorkspaceKind
    owner_id: UUID
    invite_code: str | None = None


class JoinByCodeIn(ORMModel):
    code: str = Field(min_length=4, max_length=16)


class InviteCodeOut(ORMModel):
    invite_code: str


class MemberInvite(ORMModel):
    email: EmailStr
    role: MemberRole = MemberRole.member


class MemberOut(ORMModel):
    id: UUID
    user_id: UUID
    role: MemberRole
    display_name: str
    email: EmailStr
    avatar_url: str | None = None
