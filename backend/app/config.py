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
    CLERK_JWT_ISSUER: str = ""
    CLERK_JWT_AUDIENCE: str = ""
    CLERK_JWT_AUTHORIZED_PARTIES: str = ""
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"
    VERDICT_MAX_PAYLOAD_BYTES: int = 524288

    @property
    def database_url_configured(self) -> bool:
        return bool(self.DATABASE_URL.strip())

    @property
    def uses_sqlite_database(self) -> bool:
        return self.DATABASE_URL.strip().lower().startswith("sqlite")

    @property
    def sqlite_database_allowed(self) -> bool:
        return self.APP_ENV in {"development", "test"}

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def clerk_authorized_parties(self) -> set[str]:
        return {
            party.strip()
            for party in self.CLERK_JWT_AUTHORIZED_PARTIES.split(",")
            if party.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
