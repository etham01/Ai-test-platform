"""initial users, projects, async tasks

Revision ID: 0001
Revises:
Create Date: 2026-11-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_DATETIME = mysql.DATETIME(fsp=6)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "browser_type",
            sa.String(length=32),
            server_default=sa.text("'chromium'"),
            nullable=False,
        ),
        sa.Column("scan_config", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.Column("deleted_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_projects_owner_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"], unique=False)

    op.create_table(
        "async_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "cancel_requested",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("started_at", UTC_DATETIME, nullable=True),
        sa.Column("finished_at", UTC_DATETIME, nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_async_tasks_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_async_tasks"),
    )
    op.create_index(
        "ix_async_tasks_task_id", "async_tasks", ["task_id"], unique=True
    )
    op.create_index(
        "ix_async_tasks_project_id", "async_tasks", ["project_id"], unique=False
    )
    op.create_index("ix_async_tasks_status", "async_tasks", ["status"], unique=False)

    op.create_table(
        "async_task_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("async_task_ref_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "level",
            sa.String(length=16),
            server_default=sa.text("'info'"),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=2048), nullable=False),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["async_task_ref_id"],
            ["async_tasks.id"],
            name="fk_async_task_logs_async_task_ref_id_async_tasks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_async_task_logs"),
    )
    op.create_index(
        "ix_async_task_logs_async_task_ref_id",
        "async_task_logs",
        ["async_task_ref_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO users (id, username, display_name, is_active, created_at, updated_at)
        VALUES (1, 'demo', '演示用户', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))
        ON DUPLICATE KEY UPDATE display_name = '演示用户', is_active = 1
        """
    )


def downgrade() -> None:
    op.drop_table("async_task_logs")
    op.drop_table("async_tasks")
    op.drop_table("projects")
    op.drop_table("users")
