"""allow legacy archive rows to survive account deletion, unlinked.

Account deletion erases the personal and credential fields on an account's
legacy_licenses_archive rows and unlinks them, rather than deleting the rows
outright -- the fact that a license existed stays auditable while the data that
identifies a person does not. That requires account_id to be nullable, since it
was created NOT NULL with an FK to accounts.id in 001.

token is NOT NULL and stays that way; deletion overwrites it with a marker
rather than nulling it, so an erased row is visibly erased instead of blank.

Revision ID: 004_archive_account_id_nullable
Revises: 003_unique_clerk_user_index
Create Date: 2026-09-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_archive_account_id_nullable"
down_revision = "003_unique_clerk_user_index"
branch_labels = None
depends_on = None

TABLE = "legacy_licenses_archive"


def upgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.alter_column("account_id", existing_type=sa.String(32), nullable=True)


def downgrade() -> None:
    # Rows unlinked by an account deletion cannot be re-linked -- the account
    # they referenced no longer exists. Drop them so the NOT NULL constraint can
    # be restored; there is no correct value to put back.
    op.execute(sa.text(f"DELETE FROM {TABLE} WHERE account_id IS NULL"))
    with op.batch_alter_table(TABLE) as batch:
        batch.alter_column("account_id", existing_type=sa.String(32), nullable=False)
