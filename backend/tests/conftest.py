"""Backend test harness.

Strategy:
* In-memory SQLite (StaticPool) instead of Postgres — no Docker needed.
* Dependency overrides for ``get_db`` (test session) and ``current_account``
  (a seeded test account — bypasses Clerk JWT verification).
"""

from __future__ import annotations

from dataclasses import dataclass

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
    from app.models import Account  # noqa: F401 - registers tables on Base.metadata

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": "002_free_open_source_schema"},
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
        return db.query(Account).filter(Account.id == account_id).one()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_account] = override_current_account

    client = TestClient(app)
    try:
        yield Ctx(client=client, account_id=account_id)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()
