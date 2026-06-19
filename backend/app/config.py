"""Centralized config loader - pulls from env / .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_ENV: Literal["development", "test", "production"] = "production"
    DATABASE_URL: str = ""
    CLERK_JWT_PUBLIC_KEY: str = ""

    @property
    def database_url_configured(self) -> bool:
        return bool(self.DATABASE_URL.strip())

    @property
    def uses_sqlite_database(self) -> bool:
        return self.DATABASE_URL.strip().lower().startswith("sqlite")

    @property
    def sqlite_database_allowed(self) -> bool:
        return self.APP_ENV in {"development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
