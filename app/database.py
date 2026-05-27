from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """База для всех ORM‑моделей. Импортируется моделями и Alembic."""


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    # Для SQLite в async — single connection issue: pool_pre_ping не нужен.
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Создать таблицы и легонько подмигрировать (только для dev/SQLite).
    В проде — alembic upgrade head.
    """
    from . import models  # noqa: F401
    from .models.workspace import _gen_invite_code

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ad-hoc migration: добавить недостающую колонку invite_code и бэкфиллить.
    from sqlalchemy import text
    async with engine.begin() as conn:
        # Список колонок в таблице workspaces (SQLite/Postgres-friendly через информацию о столбцах).
        try:
            rows = (await conn.execute(text("PRAGMA table_info(workspaces)"))).fetchall()
            cols = {r[1] for r in rows}
            if "invite_code" not in cols:
                await conn.execute(text("ALTER TABLE workspaces ADD COLUMN invite_code VARCHAR(16)"))
        except Exception:
            # На Postgres PRAGMA не сработает; create_all уже создаст колонку.
            pass

        # Бэкфилл: всем без invite_code раздаём уникальные коды.
        rows = (await conn.execute(text("SELECT id FROM workspaces WHERE invite_code IS NULL OR invite_code = ''"))).fetchall()
        for (wid,) in rows:
            code = _gen_invite_code()
            await conn.execute(text("UPDATE workspaces SET invite_code = :c WHERE id = :id"), {"c": code, "id": wid})
