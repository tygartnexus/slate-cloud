"""Alembic migration smoke tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return cfg


def test_migration_upgrades_paid_schema_to_free_schema(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "slate-cloud.db"
    database_url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", "test-clerk-public-key")

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    cfg = _alembic_config()

    try:
        command.upgrade(cfg, "001_initial")

        engine = sa.create_engine(database_url, future=True)
        submitted_at = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(
                sa.text("""
                    INSERT INTO accounts
                        (id, clerk_user_id, email, stripe_customer_id, created_at)
                    VALUES
                        (:id, :clerk_user_id, :email, :stripe_customer_id, :created_at)
                    """),
                {
                    "id": "acct1",
                    "clerk_user_id": "clerk_test_user",
                    "email": "test@example.com",
                    "stripe_customer_id": "cus_legacy",
                    "created_at": submitted_at,
                },
            )
            conn.execute(
                sa.text("""
                    INSERT INTO verdicts
                        (id, account_id, shot_id, final_status, is_pro, payload, submitted_at)
                    VALUES
                        (:id, :account_id, :shot_id, :final_status, :is_pro, :payload, :submitted_at)
                    """),
                {
                    "id": "verdict1",
                    "account_id": "acct1",
                    "shot_id": "shot1",
                    "final_status": "PANEL_BLOCKED",
                    "is_pro": True,
                    "payload": "{}",
                    "submitted_at": submitted_at,
                },
            )
            conn.execute(
                sa.text("""
                    INSERT INTO licenses
                        (
                            id, account_id, license_id, tier, seats, token,
                            stripe_subscription_id, issued_at, expires_at, revoked_at
                        )
                    VALUES
                        (
                            :id, :account_id, :license_id, :tier, :seats, :token,
                            :stripe_subscription_id, :issued_at, NULL, NULL
                        )
                    """),
                {
                    "id": "lic1",
                    "account_id": "acct1",
                    "license_id": "license_legacy",
                    "tier": "pro",
                    "seats": 1,
                    "token": "legacy-token",
                    "stripe_subscription_id": "sub_legacy",
                    "issued_at": submitted_at,
                },
            )

        command.upgrade(cfg, "head")

        inspector = sa.inspect(engine)
        account_columns = {
            column["name"] for column in inspector.get_columns("accounts")
        }
        verdict_columns = {
            column["name"] for column in inspector.get_columns("verdicts")
        }
        table_names = inspector.get_table_names()
        assert "licenses" not in table_names
        assert "legacy_licenses_archive" in table_names
        assert "stripe_customer_id" not in account_columns
        assert "legacy_stripe_customer_id" in account_columns
        assert "is_pro" not in verdict_columns
        assert "has_panel_review" in verdict_columns

        with engine.connect() as conn:
            value = conn.execute(
                sa.text("SELECT has_panel_review FROM verdicts WHERE id = 'verdict1'")
            ).scalar_one()
            archived_license = conn.execute(
                sa.text("SELECT token FROM legacy_licenses_archive WHERE id = 'lic1'")
            ).scalar_one()
            archived_customer = conn.execute(
                sa.text(
                    "SELECT legacy_stripe_customer_id FROM accounts WHERE id = 'acct1'"
                )
            ).scalar_one()
        assert bool(value) is True
        assert archived_license == "legacy-token"
        assert archived_customer == "cus_legacy"
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()
