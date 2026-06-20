"""Operational readiness checks for deployment gates."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db import get_sessionmaker

router = APIRouter(tags=["ops"])

CheckStatus = Literal["pass", "fail"]
OverallStatus = Literal["ready", "blocked"]


class ReadinessCheck(BaseModel):
    name: str
    status: CheckStatus
    detail: str


class ReadinessResponse(BaseModel):
    status: OverallStatus
    checks: list[ReadinessCheck]


REQUIRED_ENV_VARS = ("CLERK_JWT_PUBLIC_KEY",)
PRODUCTION_REQUIRED_ENV_VARS = (
    "CLERK_JWT_ISSUER",
    "CLERK_JWT_AUDIENCE",
    "CLERK_JWT_AUTHORIZED_PARTIES",
)
EXPECTED_ALEMBIC_REVISION = "002_free_open_source_schema"


@router.get("/ready", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    """Return deployment readiness without exposing secret values."""
    settings = get_settings()
    checks: list[ReadinessCheck] = []

    for name in REQUIRED_ENV_VARS:
        value = getattr(settings, name)
        checks.append(
            _check(
                name=name,
                ok=bool(value),
                pass_detail="configured",
                fail_detail="missing",
            )
        )
    if settings.APP_ENV == "production":
        for name in PRODUCTION_REQUIRED_ENV_VARS:
            value = getattr(settings, name)
            checks.append(
                _check(
                    name=name,
                    ok=bool(value),
                    pass_detail="configured",
                    fail_detail="missing for production JWT claim validation",
                )
            )

    checks.append(_database_config_check(settings))
    checks.append(_database_safety_check(settings))
    checks.append(_database_connectivity_check(settings))
    checks.append(_database_schema_check(settings))

    overall: OverallStatus = (
        "ready" if all(check.status == "pass" for check in checks) else "blocked"
    )
    return ReadinessResponse(status=overall, checks=checks)


def _database_config_check(settings: Settings) -> ReadinessCheck:
    return _check(
        name="DATABASE_URL",
        ok=settings.database_url_configured,
        pass_detail="configured",
        fail_detail="missing",
    )


def _database_safety_check(settings: Settings) -> ReadinessCheck:
    if not settings.database_url_configured:
        return ReadinessCheck(
            name="database_url_safety",
            status="fail",
            detail="database URL missing",
        )
    if settings.uses_sqlite_database and not settings.sqlite_database_allowed:
        return ReadinessCheck(
            name="database_url_safety",
            status="fail",
            detail="sqlite is only allowed in development/test",
        )
    return ReadinessCheck(
        name="database_url_safety",
        status="pass",
        detail=f"{settings.APP_ENV} database URL allowed",
    )


def _database_connectivity_check(settings: Settings) -> ReadinessCheck:
    if not settings.database_url_configured:
        return ReadinessCheck(
            name="database",
            status="fail",
            detail="database URL missing",
        )
    if settings.uses_sqlite_database and not settings.sqlite_database_allowed:
        return ReadinessCheck(
            name="database",
            status="fail",
            detail="unsafe database URL",
        )
    try:
        session_factory = get_sessionmaker()
        with session_factory() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return ReadinessCheck(
            name="database",
            status="fail",
            detail="query failed",
        )
    return ReadinessCheck(name="database", status="pass", detail="query ok")


def _database_schema_check(settings: Settings) -> ReadinessCheck:
    if not settings.database_url_configured:
        return ReadinessCheck(
            name="database_schema",
            status="fail",
            detail="database URL missing",
        )
    if settings.uses_sqlite_database and not settings.sqlite_database_allowed:
        return ReadinessCheck(
            name="database_schema",
            status="fail",
            detail="unsafe database URL",
        )
    try:
        session_factory = get_sessionmaker()
        with session_factory() as db:
            bind = db.get_bind()
            inspector = sa.inspect(bind)
            tables = set(inspector.get_table_names())
            if "alembic_version" not in tables:
                return ReadinessCheck(
                    name="database_schema",
                    status="fail",
                    detail="alembic version table missing",
                )
            revision = db.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
            if revision != EXPECTED_ALEMBIC_REVISION:
                return ReadinessCheck(
                    name="database_schema",
                    status="fail",
                    detail=f"expected {EXPECTED_ALEMBIC_REVISION}, got {revision or 'none'}",
                )
            if "verdicts" not in tables:
                return ReadinessCheck(
                    name="database_schema",
                    status="fail",
                    detail="verdicts table missing",
                )
            verdict_columns = {
                column["name"] for column in inspector.get_columns("verdicts")
            }
            if "has_panel_review" not in verdict_columns:
                return ReadinessCheck(
                    name="database_schema",
                    status="fail",
                    detail="verdicts.has_panel_review missing",
                )
            if "is_pro" in verdict_columns:
                return ReadinessCheck(
                    name="database_schema",
                    status="fail",
                    detail="legacy verdicts.is_pro column still present",
                )
    except Exception:
        return ReadinessCheck(
            name="database_schema",
            status="fail",
            detail="schema check failed",
        )
    return ReadinessCheck(
        name="database_schema",
        status="pass",
        detail=f"schema revision {EXPECTED_ALEMBIC_REVISION}",
    )


def _check(
    *,
    name: str,
    ok: bool,
    pass_detail: str,
    fail_detail: str,
) -> ReadinessCheck:
    return ReadinessCheck(
        name=name,
        status="pass" if ok else "fail",
        detail=pass_detail if ok else fail_detail,
    )
