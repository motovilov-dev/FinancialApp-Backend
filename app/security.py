from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

settings = get_settings()

ALGORITHM = "HS256"

# bcrypt не принимает строки длиннее 72 байт. Чтобы не падать на длинных паролях
# и быть совместимыми с менеджерами паролей — режем до 72 байт по utf-8.
_BCRYPT_MAX = 72


def _to_bcrypt_bytes(plain: str) -> bytes:
    data = plain.encode("utf-8")
    return data[:_BCRYPT_MAX]


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_to_bcrypt_bytes(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def _build(subject: UUID, purpose: str, ttl: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: UUID) -> str:
    return _build(user_id, "access", timedelta(minutes=settings.access_token_ttl_min))


def create_refresh_token(user_id: UUID) -> str:
    return _build(user_id, "refresh", timedelta(days=settings.refresh_token_ttl_days))


def create_email_verify_token(user_id: UUID, email: str) -> str:
    return _build(
        user_id,
        "email_verify",
        timedelta(hours=settings.email_verify_ttl_hours),
        extra={"email": email},
    )


def decode_token(token: str, expected_purpose: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"invalid token: {e}") from e
    if expected_purpose and payload.get("purpose") != expected_purpose:
        raise ValueError("token purpose mismatch")
    return payload
