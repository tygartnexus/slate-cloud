"""Operational readiness endpoint tests."""

from __future__ import annotations

import sqlalchemy as sa

from tests.conftest import Ctx


def _checks_by_name(body: dict) -> dict[str, dict]:
    return {check["name"]: check for check in body["checks"]}


def test_ready_endpoint_passes_with_test_configuration(ctx: Ctx) -> None:
    resp = ctx.client.get("/ready")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"

    checks = _checks_by_name(body)
    assert checks["CLERK_JWT_PUBLIC_KEY"]["status"] == "pass"
    assert checks["DATABASE_URL"]["status"] == "pass"
    assert checks["database_url_safety"]["status"] == "pass"
    assert checks["database"]["status"] == "pass"
    assert "STRIPE_API_KEY" not in checks
    assert "issuer_private_key_file" not in checks


def test_ready_endpoint_blocks_when_required_env_missing(ctx: Ctx, monkeypatch) -> None:
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", "")

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        resp = ctx.client.get("/ready")
    finally:
        get_settings.cache_clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "blocked"
    assert _checks_by_name(body)["CLERK_JWT_PUBLIC_KEY"] == {
        "name": "CLERK_JWT_PUBLIC_KEY",
        "status": "fail",
        "detail": "missing",
    }


def test_ready_endpoint_blocks_when_database_url_missing(ctx: Ctx, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "")

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    try:
        resp = ctx.client.get("/ready")
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    checks = _checks_by_name(body)
    assert body["status"] == "blocked"
    assert checks["DATABASE_URL"]["status"] == "fail"
    assert checks["database"]["detail"] == "database URL missing"


def test_ready_endpoint_blocks_sqlite_in_production(ctx: Ctx, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./should-not-be-production.db")

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    try:
        resp = ctx.client.get("/ready")
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    checks = _checks_by_name(body)
    assert body["status"] == "blocked"
    assert checks["database_url_safety"] == {
        "name": "database_url_safety",
        "status": "fail",
        "detail": "sqlite is only allowed in development/test",
    }
    assert checks["database"]["detail"] == "unsafe database URL"


def test_ready_endpoint_blocks_unmigrated_schema(
    ctx: Ctx, monkeypatch, tmp_path
) -> None:
    db_path = tmp_path / "old-schema.db"
    database_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(database_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            sa.text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            sa.text("INSERT INTO alembic_version (version_num) VALUES ('001_initial')")
        )
        conn.execute(sa.text("""
                CREATE TABLE verdicts (
                    id VARCHAR(32) PRIMARY KEY,
                    account_id VARCHAR(32),
                    shot_id VARCHAR(255),
                    final_status VARCHAR(32),
                    is_pro BOOLEAN,
                    payload JSON,
                    submitted_at DATETIME
                )
                """))

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    try:
        resp = ctx.client.get("/ready")
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    checks = _checks_by_name(body)
    assert body["status"] == "blocked"
    assert checks["database_schema"]["status"] == "fail"
    assert "expected 002_free_open_source_schema" in checks["database_schema"]["detail"]
