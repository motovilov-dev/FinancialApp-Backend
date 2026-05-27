from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models.user import User
from ..models.workspace import MemberRole, Workspace, WorkspaceKind, WorkspaceMember
from ..schemas.auth import (
    LoginIn,
    MessageOut,
    RefreshIn,
    RegisterIn,
    ResendVerifyIn,
    TokenPair,
    VerifyEmailIn,
)
from ..schemas.user import UserOut
from ..security import (
    create_access_token,
    create_email_verify_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from ..services.email import send_verify_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)) -> User:
    existing = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email уже зарегистрирован")

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        display_name=data.display_name.strip(),
        email_verified=False,
    )
    db.add(user)
    await db.flush()  # получить id

    # Создаём личный workspace по умолчанию.
    ws = Workspace(
        name="Личное",
        kind=WorkspaceKind.personal,
        owner_id=user.id,
    )
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=MemberRole.owner))

    await db.commit()
    await db.refresh(user)

    # Письмо подтверждения + приветствие. В dev — пишется в var/mail.
    token = create_email_verify_token(user.id, user.email)
    verify_url = f"{settings.public_base_url}/auth/verify-email?token={token}"
    await send_verify_email(to=user.email, display_name=user.display_name, verify_url=verify_url)
    await send_welcome_email(to=user.email, display_name=user.display_name)

    return user


@router.post("/login", response_model=TokenPair)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshIn, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        payload = decode_token(data.refresh_token, expected_purpose="refresh")
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    uid = UUID(payload["sub"])
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/verify-email", response_model=MessageOut)
async def verify_email(data: VerifyEmailIn, db: AsyncSession = Depends(get_db)) -> MessageOut:
    try:
        payload = decode_token(data.token, expected_purpose="email_verify")
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    uid = UUID(payload["sub"])
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user or user.email != payload.get("email"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Токен невалиден")
    if not user.email_verified:
        user.email_verified = True
        await db.commit()
    return MessageOut(message="Email подтверждён")


@router.post("/resend-verify", response_model=MessageOut)
async def resend_verify(data: ResendVerifyIn, db: AsyncSession = Depends(get_db)) -> MessageOut:
    user = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    # Не раскрываем существование email во избежание enumeration.
    if user and not user.email_verified:
        token = create_email_verify_token(user.id, user.email)
        verify_url = f"{settings.public_base_url}/auth/verify-email?token={token}"
        await send_verify_email(to=user.email, display_name=user.display_name, verify_url=verify_url)
    return MessageOut(message="Если email зарегистрирован, письмо отправлено")
