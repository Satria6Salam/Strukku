"""Add production search indexes.

Revision ID: 0007_production_indexes
Revises: 0006_refresh_tokens
Create Date: 2026-11-06
"""
from alembic import op

revision = "0007_production_indexes"
down_revision = "0006_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_receipt_items_receipt_category",
        "receipt_items",
        ["receipt_id", "category_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_receipts_transaction_date",
        "receipts",
        ["transaction_date"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_receipts_transaction_date", table_name="receipts", if_exists=True)
    op.drop_index("ix_receipt_items_receipt_category", table_name="receipt_items", if_exists=True)
