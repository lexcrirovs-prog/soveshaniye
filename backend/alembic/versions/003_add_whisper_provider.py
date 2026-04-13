"""Add whisper_provider to export_jobs

Revision ID: 003
Revises: 002
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("export_jobs", sa.Column("whisper_provider", sa.String(20), server_default="openai"))


def downgrade() -> None:
    op.drop_column("export_jobs", "whisper_provider")
