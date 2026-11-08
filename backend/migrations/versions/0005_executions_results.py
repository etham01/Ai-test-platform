"""executions and results

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_DATETIME = mysql.DATETIME(fsp=6)


def upgrade() -> None:
    op.create_table(
        "test_executions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "mode",
            sa.String(length=16),
            server_default=sa.text("'local'"),
            nullable=False,
        ),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            server_default=sa.text("120"),
            nullable=False,
        ),
        sa.Column("total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("passed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("errors", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("started_at", UTC_DATETIME, nullable=True),
        sa.Column("finished_at", UTC_DATETIME, nullable=True),
        sa.Column("report_path", sa.String(length=512), nullable=True),
        sa.Column("log_path", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_test_executions_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_test_executions_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_executions"),
    )
    op.create_index(
        "ix_test_executions_project_id",
        "test_executions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_executions_task_id", "test_executions", ["task_id"], unique=False
    )

    op.create_table(
        "execution_scripts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.BigInteger(), nullable=False),
        sa.Column("script_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["test_executions.id"],
            name="fk_execution_scripts_execution_id_test_executions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["script_id"],
            ["test_scripts.id"],
            name="fk_execution_scripts_script_id_test_scripts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution_scripts"),
        sa.UniqueConstraint(
            "execution_id", "script_id", name="uq_execution_scripts"
        ),
    )
    op.create_index(
        "ix_execution_scripts_execution_id",
        "execution_scripts",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_execution_scripts_script_id",
        "execution_scripts",
        ["script_id"],
        unique=False,
    )

    op.create_table(
        "test_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("script_id", sa.BigInteger(), nullable=True),
        sa.Column("test_case_id", sa.BigInteger(), nullable=True),
        sa.Column("node_id", sa.String(length=512), nullable=True),
        sa.Column("test_name", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("traceback", sa.Text(), nullable=True),
        sa.Column("screenshot_path", sa.String(length=512), nullable=True),
        sa.Column("failure_analysis", sa.JSON(), nullable=True),
        sa.Column("analysis_generation_record_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["test_executions.id"],
            name="fk_test_results_execution_id_test_executions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_test_results_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["script_id"],
            ["test_scripts.id"],
            name="fk_test_results_script_id_test_scripts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            name="fk_test_results_test_case_id_test_cases",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_generation_record_id"],
            ["generation_records.id"],
            name="fk_test_results_analysis_generation_record_id_generation_records",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_results"),
    )
    op.create_index(
        "ix_test_results_execution_id",
        "test_results",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_results_project_id", "test_results", ["project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("test_results")
    op.drop_table("execution_scripts")
    op.drop_table("test_executions")
