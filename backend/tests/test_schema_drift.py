"""Guard: the Alembic head and app/models.py must describe the same schema.

Without this, drift is invisible until someone runs `alembic revision
--autogenerate` and it silently proposes dropping real tables and columns.

Set TEST_DATABASE_URL to run these against a real engine (CI points it at
Postgres). Unset, they run against a throwaway SQLite file.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from migrations.autogen import include_object

ROOT = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return cfg


@pytest.fixture
def migrated_url(tmp_path, monkeypatch) -> Iterator[str]:
    """Yield a database URL upgraded to the Alembic head."""
    external = os.environ.get("TEST_DATABASE_URL")
    database_url = external or f"sqlite:///{(tmp_path / 'drift.db').as_posix()}"

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", "test-clerk-public-key")

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker

    for cache in (get_settings, get_engine, get_sessionmaker):
        cache.cache_clear()

    cfg = _alembic_config()
    if external:
        # Shared database: start from a known-empty schema.
        command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    try:
        yield database_url
    finally:
        if external:
            command.downgrade(cfg, "base")
        for cache in (get_settings, get_engine, get_sessionmaker):
            cache.cache_clear()


def test_models_match_migration_head(migrated_url: str) -> None:
    from app.db import Base

    engine = sa.create_engine(migrated_url, future=True)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn, opts={"include_object": include_object}
            )
            diffs = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diffs == [], (
        "Alembic head and app/models.py have drifted. Either add a migration "
        f"or exclude the object in migrations/env.py. Diff: {diffs}"
    )


def test_legacy_archive_objects_survive_migration(migrated_url: str) -> None:
    """The legacy archive must exist, not merely be absent from the diff.

    docs/deployment.md promises this data is retained; a bare "no diff" result
    would also pass if the objects had already been dropped.
    """
    engine = sa.create_engine(migrated_url, future=True)
    try:
        inspector = sa.inspect(engine)
        tables = set(inspector.get_table_names())
        account_columns = {c["name"] for c in inspector.get_columns("accounts")}
    finally:
        engine.dispose()

    assert "legacy_licenses_archive" in tables
    assert "legacy_stripe_customer_id" in account_columns


def test_clerk_user_id_index_is_unique(migrated_url: str) -> None:
    engine = sa.create_engine(migrated_url, future=True)
    try:
        indexes = sa.inspect(engine).get_indexes("accounts")
    finally:
        engine.dispose()

    match = next((i for i in indexes if i["name"] == "ix_accounts_clerk_user_id"), None)
    assert match is not None, "ix_accounts_clerk_user_id is missing"
    assert match["unique"], "clerk_user_id lookup index must be unique"
