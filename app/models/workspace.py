from __future__ import annotations

import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ._common import TimestampMixin, gen_uuid


class WorkspaceKind(str, enum.Enum):
    personal = "personal"
    team = "team"


class MemberRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


def _gen_invite_code() -> str:
    """8 символов, без визуально неоднозначных 0/O/1/I/l."""
    import secrets, string
    alphabet = "".join(c for c in (string.ascii_uppercase + string.digits) if c not in "01OIL")
    return "".join(secrets.choice(alphabet) for _ in range(8))


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[WorkspaceKind] = mapped_column(
        Enum(WorkspaceKind, native_enum=False, length=16),
        default=WorkspaceKind.personal,
        nullable=False,
    )
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=_gen_invite_code, nullable=False)


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_ws_member"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=gen_uuid)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, native_enum=False, length=16),
        default=MemberRole.member,
        nullable=False,
    )
