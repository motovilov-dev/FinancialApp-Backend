from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routers import (
    auth,
    categories,
    dashboard,
    groups,
    periods,
    snapshot,
    transactions,
    users,
    workspaces,
    ws,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # На MVP: создаём таблицы автоматически. В проде — alembic upgrade head.
    await init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
async def root():
    return {"app": settings.app_name, "env": settings.env, "version": "0.1.0"}


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(periods.router)
app.include_router(groups.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(snapshot.router)
app.include_router(dashboard.router)
app.include_router(ws.router)

# Раздача загруженных файлов (аватары и т.п.).
_UPLOADS_DIR = Path("var/uploads")
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_UPLOADS_DIR)), name="static")
