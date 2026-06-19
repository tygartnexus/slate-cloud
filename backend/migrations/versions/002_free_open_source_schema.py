"""remove paid licensing schema.

Revision ID: 002_free_open_source_schema
Revises: 001_initial
Create Date: 2026-06-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002_free_open_source_schema"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("legacy_stripe_customer_id", sa.String(64), nullable=True),
    )
    op.execute(
        sa.text("UPDATE accounts SET legacy_stripe_customer_id = stripe_customer_id")
    )

    op.add_column(
        "verdicts", sa.Column("has_panel_review", sa.Boolean(), nullable=True)
    )
    op.execute(sa.text("UPDATE verdicts SET has_panel_review = is_pro"))

    with op.batch_alter_table("verdicts") as batch:
        batch.alter_column(
            "has_panel_review", existing_type=sa.Boolean(), nullable=False
        )
        batch.drop_column("is_pro")

    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("stripe_customer_id")

    op.rename_table("licenses", "legacy_licenses_archive")


def downgrade() -> None:
    op.rename_table("legacy_licenses_archive", "licenses")

    with op.batch_alter_table("accounts") as batch:
        batch.add_column(sa.Column("stripe_customer_id", sa.String(64), nullable=True))
    op.execute(
        sa.text("UPDATE accounts SET stripe_customer_id = legacy_stripe_customer_id")
    )
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("legacy_stripe_customer_id")

    op.add_column("verdicts", sa.Column("is_pro", sa.Boolean(), nullable=True))
    op.execute(sa.text("UPDATE verdicts SET is_pro = has_panel_review"))
    with op.batch_alter_table("verdicts") as batch:
        batch.alter_column("is_pro", existing_type=sa.Boolean(), nullable=False)
        batch.drop_column("has_panel_review")
