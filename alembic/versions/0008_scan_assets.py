"""Add scan asset ownership and expiry metadata.

Revision ID: 0008_scan_assets
Revises: 0007_production_indexes
Create Date: 2026-11-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_scan_assets"
down_revision = "0007_production_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_scan_assets_id", "scan_assets", ["id"])
    op.create_index("ix_scan_assets_owner_id", "scan_assets", ["owner_id"])
    op.create_index("ix_scan_assets_storage_key", "scan_assets", ["storage_key"], unique=True)
    op.create_index("ix_scan_assets_expires_at_owner_id", "scan_assets", ["expires_at", "owner_id"])


def downgrade() -> None:
    op.drop_index("ix_scan_assets_expires_at_owner_id", table_name="scan_assets")
    op.drop_index("ix_scan_assets_storage_key", table_name="scan_assets")
    op.drop_index("ix_scan_assets_owner_id", table_name="scan_assets")
    op.drop_index("ix_scan_assets_id", table_name="scan_assets")
    op.drop_table("scan_assets")
