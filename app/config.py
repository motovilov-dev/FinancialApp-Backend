from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки приложения. Читаем из .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FinanceMac API"
    env: str = "dev"
    secret_key: str = "change-me"

    database_url: str = "sqlite+aiosqlite:///./finance.db"

    access_token_ttl_min: int = 60
    refresh_token_ttl_days: int = 30
    email_verify_ttl_hours: int = 48

    cors_origins: str = ""

    use_real_smtp: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@finance.local"
    # auto | 1 | 0 — implicit TLS. По умолчанию: True для 465, иначе STARTTLS.
    smtp_use_tls: str = "auto"
    public_base_url: str = "http://localhost:8000"

    @property
    def smtp_implicit_tls(self) -> bool:
        v = (self.smtp_use_tls or "auto").strip().lower()
        if v in ("1", "true", "yes", "on"):
            return True
        if v in ("0", "false", "no", "off"):
            return False
        return self.smtp_port == 465

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
