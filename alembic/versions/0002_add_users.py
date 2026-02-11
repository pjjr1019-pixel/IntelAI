"""Add user table for DB-backed authentication.

Revision ID: 0002_add_users
Revises: 0001_initial
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_add_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="alert",
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True, schema="alert")
    op.create_index("ix_user_email", "user", ["email"], unique=True, schema="alert")


def downgrade() -> None:
    op.drop_index("ix_user_email", table_name="user", schema="alert")
    op.drop_index("ix_user_username", table_name="user", schema="alert")
    op.drop_table("user", schema="alert")
