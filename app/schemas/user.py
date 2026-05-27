from __future__ import annotations

from uuid import UUID

from pydantic import EmailStr, Field

from ._base import ORMModel


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None = None
    email_verified: bool


class UserUpdate(ORMModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = None
