"""Skema awal (sama dengan backend versi 1 yang memakai create_all).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_categories_id", "categories", ["id"])

    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("merchant_name", sa.String(200), nullable=True),
        sa.Column("transaction_date", sa.DateTime(), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_receipts_id", "receipts", ["id"])

    op.create_table(
        "receipt_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("receipts.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("item_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("is_user_corrected", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_receipt_items_id", "receipt_items", ["id"])


def downgrade() -> None:
    op.drop_table("receipt_items")
    op.drop_table("receipts")
    op.drop_table("categories")
    op.drop_table("users")
