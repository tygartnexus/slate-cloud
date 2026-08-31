"""Operational readiness checks for deployment gates."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db import get_sessionmaker

logger = logging.getLogger(__name__)

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

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def expected_alembic_revision() -> str | None:
    """Resolve the Alembic head from the shipped migrations directory.

    Read dynamically rather than hardcoded so adding a migration cannot silently
    leave this gate asserting a stale revision. Returns None when the migrations
    directory is not shipped alongside the app, which the caller treats as a
    blocking condition rather than a pass.
    """
    script_location = BACKEND_ROOT / "migrations"
    if not script_location.is_dir():
        return None
    try:
        config = Config()
        config.set_main_option("script_location", str(script_location))
        return ScriptDirectory.from_config(config).get_current_head()
    except Exception:  # readiness must report, never raise
        logger.exception("failed to resolve alembic head from %s", script_location)
        return None


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
def readiness(response: Response) -> ReadinessResponse:
    """Return deployment readiness without exposing secret values.

    Blocked readiness is returned as 503 so orchestrator probes, deploy gates,
    and `curl -f` treat it as a failure instead of a healthy 200.
    """
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

    blocked = any(check.status == "fail" for check in checks)
    overall: OverallStatus = "blocked" if blocked else "ready"
    if blocked:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
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
    unsafe = _unsafe_database_reason(settings)
    if unsafe:
        return ReadinessCheck(name="database", status="fail", detail=unsafe)
    try:
        session_factory = get_sessionmaker()
        with session_factory() as db:
            db.execute(text("SELECT 1"))
    except Exception:  # readiness must report, never raise
        logger.exception("readiness database connectivity check failed")
        return ReadinessCheck(
            name="database",
            status="fail",
            detail="query failed",
        )
    return ReadinessCheck(name="database", status="pass", detail="query ok")


def _database_schema_check(settings: Settings) -> ReadinessCheck:
    unsafe = _unsafe_database_reason(settings)
    if unsafe:
        return ReadinessCheck(name="database_schema", status="fail", detail=unsafe)

    expected_revision = expected_alembic_revision()
    if expected_revision is None:
        return ReadinessCheck(
            name="database_schema",
            status="fail",
            detail="alembic migrations directory not found; cannot verify revision",
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
            if revision != expected_revision:
                return ReadinessCheck(
                    name="database_schema",
                    status="fail",
                    detail=f"expected {expected_revision}, got {revision or 'none'}",
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
    except Exception:  # readiness must report, never raise
        logger.exception("readiness database schema check failed")
        return ReadinessCheck(
            name="database_schema",
            status="fail",
            detail="schema check failed",
        )
    return ReadinessCheck(
        name="database_schema",
        status="pass",
        detail=f"schema revision {expected_revision}",
    )


def _unsafe_database_reason(settings: Settings) -> str | None:
    if not settings.database_url_configured:
        return "database URL missing"
    if settings.uses_sqlite_database and not settings.sqlite_database_allowed:
        return "unsafe database URL"
    return None


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
