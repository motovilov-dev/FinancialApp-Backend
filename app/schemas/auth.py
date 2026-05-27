from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class VerifyEmailIn(BaseModel):
    token: str


class ResendVerifyIn(BaseModel):
    email: EmailStr


class MessageOut(BaseModel):
    message: str
