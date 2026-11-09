"""Add security audit events.

Revision ID: 0005_security_events
Revises: 0004_password_reset
Create Date: 2026-11-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_security_events"
down_revision = "0004_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("success", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_security_events_id", "security_events", ["id"])
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_user_id", table_name="security_events")
    op.drop_index("ix_security_events_id", table_name="security_events")
    op.drop_table("security_events")
