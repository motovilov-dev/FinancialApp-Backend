# FinanceMac Backend

FastAPI + SQLAlchemy 2.0 (async) + WebSockets. На MVP — SQLite (`aiosqlite`),
готово к переезду на Postgres (`asyncpg`) сменой `DATABASE_URL`.

## Запуск (uv + Python 3.12)

```bash
cd backend
cp .env.example .env

# uv сам подтянет Python 3.12.0 (см. .python-version) и создаст .venv
uv sync

# запуск dev-сервера
uv run uvicorn app.main:app --reload --port 8000
```

Полезные команды:

```bash
uv add <package>             # добавить рантайм-зависимость
uv add --dev <package>       # добавить dev-зависимость
uv lock --upgrade            # обновить uv.lock
uv run alembic revision --autogenerate -m "..."
uv run alembic upgrade head
uv run ruff check .
uv run pytest
```

Swagger / OpenAPI: http://localhost:8000/docs

## Что внутри

- **Auth (email + пароль, JWT)** — `/auth/register`, `/auth/login`,
  `/auth/refresh`, `/auth/verify-email`, `/auth/resend-verify`.
  Письма в dev пишутся в `./var/mail/*.eml`. Включите `USE_REAL_SMTP=1` —
  поедут через SMTP (любой провайдер).
- **Multi-workspace** — `/workspaces` CRUD, члены с ролями
  `owner / admin / member`. При регистрации сразу создаётся личный workspace.
- **Финансовая модель** — periods → groups → categories → transactions.
  Все ID — UUID, клиент может приходить со своими UUID
  (offline‑first), сервер их сохраняет.
- **Snapshot** — `GET /workspaces/{wid}/snapshot` отдаёт всё дерево одним
  запросом для bootstrap'а клиента.
- **WebSocket** — `ws://host/ws/workspaces/{wid}?token=<access_jwt>`:
  - `presence` — кто сейчас в воркспейсе (Google‑style аватарки);
  - `event` — realtime CRUD‑события (entity/action/data/actor_id) после
    каждой мутации.

## Переезд на Postgres

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/finance
```

После — миграции через Alembic:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

(на MVP таблицы создаются автоматически на старте, alembic уже
сконфигурирован для прода).

## Realtime контракт (для интеграции с macOS клиентом)

Сервер → клиент:

```json
{ "type": "hello",      "user_id": "...", "workspace_id": "..." }
{ "type": "presence",   "users": [ { "user_id": "...", "display_name": "...", "avatar_url": "...", "connected_at": "...", "connections": 1 } ] }
{ "type": "event",      "entity": "transaction", "action": "created", "actor_id": "...", "data": { ... } }
{ "type": "pong" }
```

Клиент → сервер: `{ "type": "ping" }` (keep‑alive). Все мутации идут через
REST; WebSocket — только канал нотификаций и presence.

## TODO следующего шага

- Email‑инвайты участников + magic‑link логин.
- Avatars upload (S3/MinIO).
- Долго живущие сессии (refresh rotation, device list).
- Заменить in‑memory pub/sub на Redis для горизонтального масштабирования.
- Гранулярные пермишены (заморозка закрытых периодов на уровне БД триггерами).
