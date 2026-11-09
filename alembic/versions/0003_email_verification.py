"""Add email verification fields to users.

Revision ID: 0003_email_verification
Revises: 0002_v2_schema
Create Date: 2026-11-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_email_verification"
down_revision = "0002_v2_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "is_email_verified",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))

    # Existing accounts remain verified so this upgrade does not lock them out.
    op.execute("UPDATE users SET is_email_verified = 1 WHERE is_email_verified = 0")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified_at")
        batch.drop_column("is_email_verified")
