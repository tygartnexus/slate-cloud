"""Backend test harness.

Strategy:
* In-memory SQLite (StaticPool) instead of Postgres — no Docker needed.
* Dependency overrides for ``get_db`` (test session) and ``current_account``
  (a seeded test account — bypasses Clerk JWT verification).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@dataclass
class Ctx:
    client: TestClient
    account_id: str
    # Sessionmaker bound to the test database, for asserting on rows directly:
    #   with ctx.session() as db: ...
    session: Any


@dataclass
class OtherAccount:
    """A second account, to prove endpoints cannot reach across accounts."""

    account_id: str
    verdict_id: str


@pytest.fixture
def ctx(tmp_path, monkeypatch) -> Ctx:
    # 1. Env -> settings (clear the lru_cache so they take effect).
    database_url = f"sqlite:///{(tmp_path / 'slate-cloud-test.db').as_posix()}"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", "test-clerk-public-key")

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    # 2. In-memory SQLite shared across connections. Import the models module
    #    BEFORE create_all so every table is registered on Base.metadata.
    from app.db import Base, get_db
    from app.models import Account

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # Stamp the real Alembic head rather than a hardcoded revision, so adding a
    # migration cannot leave the readiness tests asserting a stale value.
    from app.routes.readiness import expected_alembic_revision

    with engine.begin() as conn:
        conn.execute(text("""
                CREATE TABLE legacy_licenses_archive (
                    id VARCHAR(32) PRIMARY KEY,
                    account_id VARCHAR(32) NULL REFERENCES accounts(id),
                    license_id VARCHAR(64) NOT NULL UNIQUE,
                    tier VARCHAR(16) NOT NULL,
                    seats INTEGER NOT NULL,
                    token VARCHAR(2048) NOT NULL,
                    stripe_subscription_id VARCHAR(64) NULL,
                    issued_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NULL,
                    revoked_at TIMESTAMP NULL
                )
                """))
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": expected_alembic_revision()},
        )
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    # 3. Seed one account.

    seed = TestSession()
    account = Account(clerk_user_id="clerk_test_user", email="test@example.com")
    seed.add(account)
    seed.commit()
    account_id = account.id
    seed.close()

    # 4. Dependency overrides.
    from app.auth.clerk import current_account
    from app.main import app

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    def override_current_account(db: Session = Depends(get_db)) -> Account:
        # Mirrors app.auth.clerk.current_account: resolve by Clerk user id and
        # create on first-seen. A hard lookup by the seeded row id would raise
        # instead of recreating once a test deletes the account.
        account = (
            db.query(Account)
            .filter(Account.clerk_user_id == "clerk_test_user")
            .one_or_none()
        )
        if account is None:
            account = Account(clerk_user_id="clerk_test_user", email="test@example.com")
            db.add(account)
            db.commit()
            db.refresh(account)
        return account

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_account] = override_current_account

    client = TestClient(app)
    try:
        yield Ctx(client=client, account_id=account_id, session=TestSession)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()


@pytest.fixture
def other_account(ctx: Ctx) -> OtherAccount:
    """Seed a second account owning one verdict."""
    from app.models import Account, VerdictRecord

    with ctx.session() as db:
        account = Account(clerk_user_id="clerk_other_user", email="other@example.com")
        db.add(account)
        db.commit()
        db.refresh(account)
        verdict = VerdictRecord(
            account_id=account.id,
            shot_id="not_yours",
            final_status="PASS",
            has_panel_review=False,
            payload={"shot_id": "not_yours"},
        )
        db.add(verdict)
        db.commit()
        db.refresh(verdict)
        return OtherAccount(account_id=account.id, verdict_id=verdict.id)


@pytest.fixture
def legacy_license(ctx: Ctx) -> str:
    """Give the test account one legacy archive row, as migration 002 would leave."""
    row_id = "lic_legacy_1"
    with ctx.session() as db:
        db.execute(
            text("""
                INSERT INTO legacy_licenses_archive
                    (id, account_id, license_id, tier, seats, token,
                     stripe_subscription_id, issued_at)
                VALUES
                    (:id, :account_id, :license_id, :tier, :seats, :token,
                     :stripe_subscription_id, :issued_at)
                """),
            {
                "id": row_id,
                "account_id": ctx.account_id,
                "license_id": "license_legacy",
                "tier": "pro",
                "seats": 1,
                "token": "signed.legacy.token.value",
                "stripe_subscription_id": "sub_legacy",
                "issued_at": datetime.now(timezone.utc),
            },
        )
        db.commit()
    return row_id
