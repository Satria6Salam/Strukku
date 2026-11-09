"""Skema v2: tampilan kategori, jumlah barang, jejak prediksi ML, index.

Revision ID: 0002_v2_schema
Revises: 0001_baseline
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_v2_schema"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("categories") as batch:
        batch.add_column(sa.Column("display_name", sa.String(100), nullable=True))
        batch.add_column(sa.Column("icon", sa.String(50), nullable=True))
        batch.add_column(sa.Column("color", sa.String(9), nullable=True))
        batch.add_column(sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))

    with op.batch_alter_table("receipts") as batch:
        batch.add_column(sa.Column("raw_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_receipts_user_id_transaction_date", ["user_id", "transaction_date"])

    with op.batch_alter_table("receipt_items") as batch:
        batch.add_column(sa.Column("quantity", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("predicted_category_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("prediction_source", sa.String(30), nullable=True))
        batch.create_foreign_key(
            "fk_receipt_items_predicted_category_id_categories",
            "categories",
            ["predicted_category_id"],
            ["id"],
        )
        batch.create_index("ix_receipt_items_receipt_id", ["receipt_id"])
        batch.create_index("ix_receipt_items_category_id", ["category_id"])


def downgrade() -> None:
    with op.batch_alter_table("receipt_items") as batch:
        batch.drop_index("ix_receipt_items_category_id")
        batch.drop_index("ix_receipt_items_receipt_id")
        batch.drop_constraint("fk_receipt_items_predicted_category_id_categories", type_="foreignkey")
        batch.drop_column("prediction_source")
        batch.drop_column("predicted_category_id")
        batch.drop_column("quantity")

    with op.batch_alter_table("receipts") as batch:
        batch.drop_index("ix_receipts_user_id_transaction_date")
        batch.drop_column("updated_at")
        batch.drop_column("raw_text")

    with op.batch_alter_table("categories") as batch:
        for col in ("is_active", "sort_order", "color", "icon", "display_name"):
            batch.drop_column(col)

    with op.batch_alter_table("users") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("is_active")
