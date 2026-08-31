"""normalise the clerk_user_id uniqueness to a single unique index.

Migration 001 declared the column UNIQUE *and* created a separate plain index.
On PostgreSQL that produced two redundant enforcements of the same rule --
constraint ``accounts_clerk_user_id_key`` plus index ``ix_accounts_clerk_user_id``
-- while app/models.py declares a single ``unique=True, index=True`` column.
SQLite does not surface the column-level UNIQUE as a droppable constraint, which
is why the mismatch only appears against PostgreSQL.

Uniqueness was always enforced, so this is not a data-integrity fix. It removes
the drift between the migration head and the models so the guard in
tests/test_schema_drift.py can assert an empty diff on both engines.

Revision ID: 003_unique_clerk_user_index
Revises: 002_free_open_source_schema
Create Date: 2026-08-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_unique_clerk_user_index"
down_revision = "002_free_open_source_schema"
branch_labels = None
depends_on = None

TABLE = "accounts"
COLUMN = "clerk_user_id"
INDEX = "ix_accounts_clerk_user_id"


def _clerk_user_unique_constraints() -> list[str]:
    """Named UNIQUE constraints on accounts.clerk_user_id, if the dialect has them."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return []
    names: list[str] = []
    for constraint in sa.inspect(bind).get_unique_constraints(TABLE):
        name = constraint.get("name")
        if name and constraint["column_names"] == [COLUMN]:
            names.append(name)
    return names


def upgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
    op.create_index(INDEX, TABLE, [COLUMN], unique=True)
    for name in _clerk_user_unique_constraints():
        op.drop_constraint(name, TABLE, type_="unique")


def downgrade() -> None:
    # Guarded: a database that predates this revision may still carry the
    # constraint, in which case there is nothing to restore.
    is_postgres = op.get_bind().dialect.name == "postgresql"
    if is_postgres and not _clerk_user_unique_constraints():
        op.create_unique_constraint("accounts_clerk_user_id_key", TABLE, [COLUMN])
    op.drop_index(INDEX, table_name=TABLE)
    op.create_index(INDEX, TABLE, [COLUMN])
