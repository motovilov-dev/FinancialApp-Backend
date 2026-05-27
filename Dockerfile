FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Системные зависимости для cryptography/bcrypt и т.п.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv (https://docs.astral.sh/uv/)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Устанавливаем зависимости отдельно для кэширования слоёв
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
RUN uv sync

# Код приложения
COPY app /app/app
# alembic.ini опционально (если будете включать миграции позже)
COPY alembic.ini /app/alembic.ini

# Папки для uploads и локальной SQLite (если используется)
RUN mkdir -p /app/var/uploads /app/var/db && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# В проде лучше запускать миграции отдельной задачей,
# но на MVP держим auto-init_db() в lifespan.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

