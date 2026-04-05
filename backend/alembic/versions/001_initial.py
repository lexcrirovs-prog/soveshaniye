"""Initial migration - create all tables

Revision ID: 001
Revises:
Create Date: 2026-04-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Employees
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bitrix_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255)),
        sa.Column("position", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Export Jobs
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("date_from", sa.DateTime(timezone=True)),
        sa.Column("date_to", sa.DateTime(timezone=True)),
        sa.Column("department_id", sa.Integer()),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("total_calls", sa.Integer(), server_default="0"),
        sa.Column("processed", sa.Integer(), server_default="0"),
        sa.Column("error_msg", sa.Text()),
        sa.Column("report_path", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Sales Scripts
    op.create_table(
        "sales_scripts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("original_file", sa.String(512)),
        sa.Column("file_type", sa.String(10)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Calls
    op.create_table(
        "calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bitrix_call_id", sa.String(64), unique=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("phone_number", sa.String(32)),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("call_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("audio_path", sa.String(512)),
        sa.Column("deal_id", sa.Integer()),
        sa.Column("deal_name", sa.String(512)),
        sa.Column("deal_stage", sa.String(128)),
        sa.Column("deal_amount", sa.Float()),
        sa.Column("status", sa.String(20), server_default="new"),
        sa.Column("export_job_id", sa.Integer(), sa.ForeignKey("export_jobs.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calls_employee_id", "calls", ["employee_id"])
    op.create_index("ix_calls_call_date", "calls", ["call_date"])

    # Transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "call_id",
            sa.Integer(),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), server_default="ru"),
        sa.Column("model_used", sa.String(32), server_default="small"),
        sa.Column("confidence", sa.Float()),
        sa.Column("segments", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Analyses
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "call_id",
            sa.Integer(),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
        ),
        sa.Column("script_id", sa.Integer(), sa.ForeignKey("sales_scripts.id"), nullable=True),
        sa.Column("greeting_score", sa.SmallInteger()),
        sa.Column("needs_discovery", sa.SmallInteger()),
        sa.Column("presentation_score", sa.SmallInteger()),
        sa.Column("objection_handling", sa.SmallInteger()),
        sa.Column("closing_score", sa.SmallInteger()),
        sa.Column("initiative_score", sa.SmallInteger()),
        sa.Column("overall_score", sa.SmallInteger()),
        sa.Column("summary", sa.Text()),
        sa.Column("strengths", postgresql.JSONB()),
        sa.Column("weaknesses", postgresql.JSONB()),
        sa.Column("recommendations", postgresql.JSONB()),
        sa.Column("missed_script_steps", postgresql.JSONB()),
        sa.Column("who_leads", sa.String(20)),
        sa.Column("next_step_agreed", sa.Boolean()),
        sa.Column("crm_note_suggestion", sa.Text()),
        sa.Column("raw_response", sa.Text()),
        sa.Column("model_used", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_analyses_call_id", "analyses", ["call_id"])


def downgrade() -> None:
    op.drop_table("analyses")
    op.drop_table("transcripts")
    op.drop_table("calls")
    op.drop_table("sales_scripts")
    op.drop_table("export_jobs")
    op.drop_table("employees")
