"""llm configs, generation records, requirements, workflows, test cases

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_DATETIME = mysql.DATETIME(fsp=6)


def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=32),
            server_default=sa.text("'mock'"),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column(
            "model",
            sa.String(length=128),
            server_default=sa.text("'mock-v1'"),
            nullable=False,
        ),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("api_key_hint", sa.String(length=16), nullable=True),
        sa.Column(
            "temperature", sa.Float(), server_default=sa.text("0.2"), nullable=False
        ),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            server_default=sa.text("60"),
            nullable=False,
        ),
        sa.Column(
            "max_retries", sa.Integer(), server_default=sa.text("2"), nullable=False
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_llm_configs_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_llm_configs"),
    )
    op.create_index(
        "ix_llm_configs_project_id", "llm_configs", ["project_id"], unique=True
    )

    op.create_table(
        "generation_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column(
            "is_mock",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("raw_response_path", sa.String(length=512), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_generation_records_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_generation_records"),
    )
    op.create_index(
        "ix_generation_records_project_id",
        "generation_records",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_generation_records_task_type",
        "generation_records",
        ["task_type"],
        unique=False,
    )

    op.create_table(
        "test_requirements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("related_page_ids", sa.JSON(), nullable=True),
        sa.Column("generation_config", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.Column("deleted_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_test_requirements_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_test_requirements_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_requirements"),
    )
    op.create_index(
        "ix_test_requirements_project_id",
        "test_requirements",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_requirements_deleted_at",
        "test_requirements",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "workflows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("requirement_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("involved_page_ids", sa.JSON(), nullable=True),
        sa.Column("uncertainty", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'inferred'"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("generation_record_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.Column("deleted_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_workflows_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["test_requirements.id"],
            name="fk_workflows_requirement_id_test_requirements",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["generation_record_id"],
            ["generation_records.id"],
            name="fk_workflows_generation_record_id_generation_records",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflows"),
    )
    op.create_index("ix_workflows_project_id", "workflows", ["project_id"], unique=False)
    op.create_index("ix_workflows_deleted_at", "workflows", ["deleted_at"], unique=False)

    op.create_table(
        "test_cases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("requirement_id", sa.BigInteger(), nullable=True),
        sa.Column("case_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("module", sa.String(length=128), nullable=True),
        sa.Column(
            "priority",
            sa.String(length=16),
            server_default=sa.text("'P2'"),
            nullable=False,
        ),
        sa.Column("preconditions", sa.JSON(), nullable=True),
        sa.Column("related_page_ids", sa.JSON(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("test_data", sa.JSON(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("assertions", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "generation_source",
            sa.String(length=32),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
        sa.Column("generation_record_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.Column("deleted_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_test_cases_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["test_requirements.id"],
            name="fk_test_cases_requirement_id_test_requirements",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["generation_record_id"],
            ["generation_records.id"],
            name="fk_test_cases_generation_record_id_generation_records",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_cases"),
        sa.UniqueConstraint("project_id", "case_code", name="uq_test_cases_project_code"),
    )
    op.create_index("ix_test_cases_project_id", "test_cases", ["project_id"], unique=False)
    op.create_index(
        "ix_test_cases_requirement_id",
        "test_cases",
        ["requirement_id"],
        unique=False,
    )
    op.create_index("ix_test_cases_deleted_at", "test_cases", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_table("test_cases")
    op.drop_table("workflows")
    op.drop_table("test_requirements")
    op.drop_table("generation_records")
    op.drop_table("llm_configs")
