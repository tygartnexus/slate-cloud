"""Autogenerate filters shared by Alembic and the schema-drift test.

Kept out of env.py because env.py touches ``alembic.context``, which only exists
while a migration is running and therefore cannot be imported from a test.
"""

from __future__ import annotations

from typing import Any

# Objects kept in the database for auditability but deliberately not mapped in
# app/models.py (see docs/deployment.md). Without this exclusion, the next
# `alembic revision --autogenerate` proposes dropping them, which would destroy
# the archived commercial data migration 002 was written to preserve.
LEGACY_ARCHIVE_TABLES = frozenset({"legacy_licenses_archive"})
LEGACY_ARCHIVE_COLUMNS = frozenset({("accounts", "legacy_stripe_customer_id")})


def include_object(
    obj: Any,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    """Return False for objects autogenerate must leave alone."""
    if type_ == "table" and name in LEGACY_ARCHIVE_TABLES:
        return False
    if type_ in {"column", "index"}:
        table_name = getattr(getattr(obj, "table", None), "name", None)
        if type_ == "column" and (table_name, name) in LEGACY_ARCHIVE_COLUMNS:
            return False
        if type_ == "index" and table_name in LEGACY_ARCHIVE_TABLES:
            return False
    return True
